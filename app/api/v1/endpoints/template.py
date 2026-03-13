import json
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.routing import APIRouter

router = APIRouter(tags=["Templates"])


@router.get("/client-setup.json")
async def get_client_template(request: Request, tenant_id: str | None = None):
    """
    고객사(Client) 구독에 Azure Functions를 배포하기 위해 참조하는 ARM 템플릿입니다.
    """
    template_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "infra"
        / "client"
        / "client-setup.json"
    )

    import anyio

    path = anyio.Path(template_path)
    if not await path.exists():
        raise HTTPException(
            status_code=404, detail="Client setup template file not found"
        )

    template_data = json.loads(await path.read_text(encoding="utf-8"))

    # 1. 외부 파라미터 제어 (Azure Portal UI에서 불필요하거나 고정된 값 숨기기)
    # 포털의 '기본' 탭에서 아예 보이지 않도록 parameters 블록에서 제거합니다.
    # [주의] appName과 resourceGroupName은 사용자가 직접 입력해야 하므로 제거 목록에서 제외합니다.
    for param_to_del in [
        "env",
        "providerUrl",
        "packageUrl",
        "providerClientId",
        "providerPrincipalId",  # 완전히 제거하여 UI 노출을 차단합니다.
        "deploymentId",
    ]:
        if param_to_del in template_data.get("parameters", {}):
            del template_data["parameters"][param_to_del]

    # 2. 클라이언트 내부 리소스 배포 파라미터에 고정 값 하드코딩 (변조 방지)
    # 사용자가 포털에서 바꿀 수 없도록 백엔드에서 값을 직접 주입합니다.
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
            resource["resourceGroup"] = "[parameters('resourceGroupName')]"
            inner_params = resource.get("properties", {}).get("parameters", {})

            # Provider 백엔드 URL 주입
            if "providerUrl" in inner_params:
                inner_params["providerUrl"]["value"] = base_url
            # Provider App Registration Client ID 주입
            if "providerClientId" in inner_params:
                inner_params["providerClientId"]["value"] = settings.CLIENT_ID
            # Provider Service Principal Object ID를 Variable로 전환하여 UI에서 완전히 숨깁니다.
            if tenant_id:
                from app.core.auth.dependencies import get_graph_service
                graph_service = get_graph_service()
                try:
                    sp_id = await graph_service.get_own_service_principal_id(tenant_id=tenant_id)
                    # 1. Variables에 주입
                    if "variables" not in template_data:
                        template_data["variables"] = {}
                    template_data["variables"]["providerPrincipalId"] = sp_id
                except Exception as e:
                    import structlog
                    structlog.get_logger().error("Failed to discover tenant-specific SP ID for template", tenant_id=tenant_id, error=str(e))

            # [핵심] 상위 템플릿의 파라미터에서 제거된 providerPrincipalId를 변수 참조로 연결합니다.
            if "providerPrincipalId" in inner_params:
                inner_params["providerPrincipalId"]["value"] = "[variables('providerPrincipalId')]"

            # 에이전트 소스 패키지(Zip) URL 주입
            if "packageUrl" in inner_params:
                import jwt

                download_token = jwt.encode(
                    {"purpose": "agent-package-download"},
                    settings.DOWNLOAD_SECRET_KEY,
                    algorithm="HS256",
                )
                package_download_url = f"{base_url}/api/v1/packages/download?version=latest&token={download_token}"
                inner_params["packageUrl"]["value"] = package_download_url

    return JSONResponse(
        content=template_data,
        headers={
            "Access-Control-Allow-Origin": "*",
        },
    )
