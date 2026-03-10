import json
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.routing import APIRouter

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get("/client-setup.json")
async def get_client_template(request: Request):
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
    for param_to_del in [
        "providerUrl",
        "packageUrl",
        "providerClientId",
        "deploymentId",
    ]:
        if param_to_del in template_data.get("parameters", {}):
            del template_data["parameters"][param_to_del]

    # 2. 클라이언트 내부 리소스 배포 파라미터에 고정 값 하드코딩 (변조 방지)
    # Azure Container Apps 환경 등에서는 항상 HTTPS를 사용하도록 강제합니다.
    scheme = request.url.scheme
    if "azurecontainerapps.io" in request.url.netloc or not settings.DEBUG:
        scheme = "https"

    base_url = f"{scheme}://{request.url.netloc}"

    for resource in template_data.get("resources", []):
        if resource.get("type") == "Microsoft.Resources/deployments":
            inner_params = resource.get("properties", {}).get("parameters", {})
            # Provider 백엔드 URL 주입
            if "providerUrl" in inner_params:
                inner_params["providerUrl"]["value"] = base_url
            # Provider App Registration Client ID 주입 (에이전트 Bearer 토큰 획득용 Audience)
            if "providerClientId" in inner_params:
                inner_params["providerClientId"]["value"] = settings.CLIENT_ID
            # 에이전트 소스 패키지(Zip) URL 주입
            if "packageUrl" in inner_params:
                # 다운로드 스크래핑을 방지하기 위한 토큰.
                # Function App 특성상 재시작/스케일아웃 시마다 WEBSITE_RUN_FROM_PACKAGE 원본 URL에 재접근하므로,
                # 만료 시간(exp)을 설정하면 향후 앱이 중단될 위험이 있어 만료를 설정하지 않습니다.
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
