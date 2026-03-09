import json
from datetime import UTC, datetime
from urllib.parse import quote

from app.core.auth.models import Identity
from app.domains.package.repository import AgentPackageRepository
from app.infra.external.azure.azure_resource_service import AzureResourceService

from ..schemas import SubscriptionSetupResponse


class GetSubscriptionSetupInfoUseCase:
    """
    구독별 인프라 설치를 위한 템플릿 URL 및 Portal 배포 링크를 생성합니다.
    실제 배포 권한(Owner/Contributor)이 있는지도 사전에 검증합니다.
    """

    def __init__(
        self,
        repository: AgentPackageRepository,
        azure_service: AzureResourceService,
    ):
        self.repository = repository
        self.azure_service = azure_service

    async def execute(
        self, subscription_id: str, base_url: str, identity: Identity
    ) -> SubscriptionSetupResponse:
        bicep_url = f"{base_url}/api/v1/templates/client-setup.json"

        package_info = await self.repository.get_latest()
        package_url = f"{base_url}{package_info.url}" if package_info else ""

        parameters = {
            "resourceGroupName": {"value": f"rg-logdoctor-{subscription_id[:8]}"},
            "appName": {"value": f"logdr-client-{subscription_id[:8]}"},
            "env": {"value": "prod"},
            "providerUrl": {"value": base_url},
            "packageUrl": {"value": package_url},
            "deploymentId": {"value": datetime.now(UTC).strftime("%Y%m%d%H%M%S")},
        }

        # 4. Azure 배포 권한(RBAC) 실시간 검증
        if not identity.sso_token:
            has_permission, reason = (
                False,
                "인증 정보가 부족합니다. 다시 로그인해주세요.",
            )
        else:
            (
                has_permission,
                reason,
            ) = await self.azure_service.check_deployment_permission(
                identity.sso_token, subscription_id
            )

        # 5. Azure Portal 'Deploy to Azure' 링크 생성
        portal_link = ""
        if has_permission:
            encoded_uri = quote(bicep_url, safe="")
            encoded_params = quote(json.dumps(parameters), safe="")
            portal_link = (
                f"https://portal.azure.com/#create/Microsoft.Template/uri/{encoded_uri}"
                f"/targetScope/subscription"
                f"/parameters/{encoded_params}"
            )

        return SubscriptionSetupResponse(
            bicep_url=bicep_url,
            parameters=parameters,
            portal_link=portal_link,
            has_deployment_permission=has_permission,
            reason=reason,
        )
