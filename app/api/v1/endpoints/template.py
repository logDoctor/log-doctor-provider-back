import json
from pathlib import Path

import anyio
from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.auth.dependencies import get_graph_service
from app.core.config import settings
from app.core.routing import APIRouter
from app.domains.package.dependencies import get_agent_package_repository
from app.domains.package.repository import AgentPackageRepository

router = APIRouter(tags=["Templates"])





@router.get("/client-setup.json")
async def get_client_template(
    request: Request,
    tenant_id: str | None = None,
    package_repository: AgentPackageRepository = Depends(get_agent_package_repository),
):
    """
    고객사(Client) 구독에 Azure Functions를 배포하기 위해 참조하는 ARM 템플릿입니다.
    """
    template_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "infra"
        / "client"
        / "client-setup.json"
    )

    path = anyio.Path(template_path)
    if not await path.exists():
        raise HTTPException(
            status_code=404, detail="Client setup template file not found"
        )

    template_data = json.loads(await path.read_text(encoding="utf-8"))

    # 1. 외부 파라미터 제어 (Azure Portal UI에서 불필요하거나 고정된 값 숨기기)
    # 포털의 '기본' 탭에서 아예 보이지 않도록 parameters 블록에서 제거합니다.
    # [주의] resourceGroupName은 사용자가 직접 입력해야 하므로 제거 목록에서 제외합니다.
    # appName은 고정값('logdoctor')이므로 파라미터에서 제거하고 variables에 주입합니다.
    for param_to_del in [
        "env",
        "appName",
        "publisherUrl",
        "packageUrl",
        "publisherClientId",
        "publisherPrincipalId",  # 완전히 제거하여 UI 노출을 차단합니다.
    ]:
        if param_to_del in template_data.get("parameters", {}):
            del template_data["parameters"][param_to_del]

    # appName을 variables로 이관하여 parameters 참조를 유지합니다.
    if "variables" not in template_data:
        template_data["variables"] = {}
    template_data["variables"]["appName"] = "logdoctor"

    # variables 블록 내의 parameters('appName') 참조를 variables('appName')으로 치환합니다.
    for key, value in template_data.get("variables", {}).items():
        if isinstance(value, str):
            template_data["variables"][key] = value.replace(
                "parameters('appName')", "variables('appName')"
            )




    scheme = request.url.scheme
    if "azurecontainerapps.io" in request.url.netloc or not settings.DEBUG:
        scheme = "https"

    base_url = f"{scheme}://{request.url.netloc}"

    # 상위 레벨 리소스(Resource Group 등)에서 파라미터 참조 복구
    for resource in template_data.get("resources", []):
        # 리소스 그룹 생성 (파라미터 참조 유지)
        if resource.get("type") == "Microsoft.Resources/resourceGroups":
            resource["name"] = "[parameters('resourceGroupName')]"

        # 중첩 배포 (파라미터 참조 유지)
        if resource.get("type") == "Microsoft.Resources/deployments":
            # 이미 리소스 그룹 스코프인 경우에만 파라미터로 복구 (구독 레벨 배포는 건드리지 않음)
            if "resourceGroup" in resource:
                resource["resourceGroup"] = "[parameters('resourceGroupName')]"
            inner_params = resource.get("properties", {}).get("parameters", {})

            # Provider 백엔드 URL 주입
            if "publisherUrl" in inner_params:
                inner_params["publisherUrl"]["value"] = base_url
            # Provider App Registration Client ID 주입
            if "publisherClientId" in inner_params:
                inner_params["publisherClientId"]["value"] = settings.CLIENT_ID
            # Provider Service Principal Object ID를 Variable로 전환하여 UI에서 완전히 숨깁니다.
            if tenant_id:
                graph_service = get_graph_service()
                try:
                    sp_id = await graph_service.get_own_service_principal_id(
                        tenant_id=tenant_id
                    )
                    # 1. Variables에 주입
                    if "variables" not in template_data:
                        template_data["variables"] = {}
                    template_data["variables"]["publisherPrincipalId"] = sp_id
                except Exception as e:
                    import structlog

                    structlog.get_logger().error(
                        "Failed to discover tenant-specific SP ID for template",
                        tenant_id=tenant_id,
                        error=str(e),
                    )

            # [핵심] 상위 템플릿의 파라미터에서 제거된 publisherPrincipalId를 변수 참조로 연결합니다.
            if "publisherPrincipalId" in inner_params:
                inner_params["publisherPrincipalId"]["value"] = (
                    "[variables('publisherPrincipalId')]"
                )

            # 에이전트 소스 패키지(Zip) URL 주입
            if "packageUrl" in inner_params:
                import jwt

                # 📌 복사 당시의 최신 패키지 버전을 동결(Freeze)하여 주입합니다.
                try:
                    latest_pkg = await package_repository.get_by_version("latest")
                    version_str = latest_pkg.version if latest_pkg else "latest"
                except Exception:
                    version_str = "latest"

                download_token = jwt.encode(
                    {"purpose": "agent-package-download"},
                    settings.DOWNLOAD_SECRET_KEY,
                    algorithm="HS256",
                )
                package_download_url = f"{base_url}/api/v1/packages/download?version={version_str}&token={download_token}"
                inner_params["packageUrl"]["value"] = package_download_url

    return JSONResponse(
        content=template_data,
        headers={
            "Access-Control-Allow-Origin": "*",
        },
    )
