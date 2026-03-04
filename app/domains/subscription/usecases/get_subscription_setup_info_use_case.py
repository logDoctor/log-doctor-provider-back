import json
from datetime import UTC, datetime
from urllib.parse import quote

from app.domains.package.usecases import GetPackageUseCase

from ..schemas import SubscriptionSetupResponse


class GetSubscriptionSetupInfoUseCase:
    """
    구독별 인프라 설치를 위한 템플릿 URL 및 Portal 배포 링크를 생성합니다.
    """

    def __init__(self, package_use_case: GetPackageUseCase):
        self.package_use_case = package_use_case

    async def execute(
        self, subscription_id: str, base_url: str
    ) -> SubscriptionSetupResponse:
        # 1. 고객사 전용 템플릿 URL (백엔드 서빙 경로)
        bicep_url = f"{base_url}/api/v1/templates/client-setup.json"

        # 2. 최신 패키지 URL 가져오기
        package_info = await self.package_use_case.execute()
        # Full URL 생성을 위해 base_url 결합 (현재 repo는 상대경로 반환하므로)
        package_url = f"{base_url}{package_info.url}" if package_info else ""

        # 3. 설치 파라미터 구성
        parameters = {
            "resourceGroupName": {"value": "rg-logdoctor-client"},
            "appName": {"value": "logdoctor-client"},
            "env": {"value": "prod"},
            "providerUrl": {"value": base_url},
            "packageUrl": {"value": package_url},
            "deploymentId": {"value": datetime.now(UTC).strftime("%Y%m%d%H%M%S")},  # 🚀 [FIX] 매 배포마다 설정을 변경하여 재시작 유도
        }

        # 4. Azure Portal 'Deploy to Azure' 링크 생성
        encoded_uri = quote(bicep_url, safe="")
        encoded_params = quote(json.dumps(parameters), safe="")

        # 구독 수준 배포를 위해 /targetScope/subscription 추가
        portal_link = (
            f"https://portal.azure.com/#create/Microsoft.Template/uri/{encoded_uri}"
            f"/targetScope/subscription"
            f"/parameters/{encoded_params}"
        )

        return SubscriptionSetupResponse(
            bicep_url=bicep_url, parameters=parameters, portal_link=portal_link
        )
