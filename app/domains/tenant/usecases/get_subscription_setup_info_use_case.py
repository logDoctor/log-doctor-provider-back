import json
from datetime import UTC, datetime
from urllib.parse import quote

from app.core.auth.models import Identity
from app.core.interfaces.azure_arm import AzureArmService
from app.domains.package.repository import AgentPackageRepository
from app.domains.tenant.schemas import SubscriptionSetupResponse


class GetSubscriptionSetupInfoUseCase:
    """구독별 인프라 설치를 위한 템플릿 URL 및 Portal 배포 링크를 생성합니다."""

    def __init__(
        self,
        repository: AgentPackageRepository,
        azure_arm_service: AzureArmService,
    ):
        self.repository = repository
        self.azure_arm_service = azure_arm_service

    async def execute(
        self, subscription_id: str, base_url: str, identity: Identity
    ) -> SubscriptionSetupResponse:
        bicep_url = f"{base_url}/api/v1/templates/client-setup.json"

        package_info = await self.repository.get_by_version("latest")
        package_url = f"{base_url}{package_info.url}" if package_info else ""

        parameters = {
            "resourceGroupName": {"value": f"rg-logdoctor-{subscription_id[:8]}"},
            "appName": {"value": f"logdr-client-{subscription_id[:8]}"},
            "env": {"value": "prod"},
            "providerUrl": {"value": base_url},
            "packageUrl": {"value": package_url},
            "deploymentId": {"value": datetime.now(UTC).strftime("%Y%m%d%H%M%S")},
        }

        try:
            await self.azure_arm_service.check_deployment_permission(
                identity.sso_token, subscription_id
            )
            has_permission = True
            reason = None
        except Exception as e:
            has_permission = False
            reason = str(e)

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
