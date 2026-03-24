import json
import time
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
        # 🔗 Azure Portal 캐싱 방지를 위해 버전을 타임스탬프로 붙여서 고유화합니다.
        bicep_url = f"{base_url}/api/v1/templates/client-setup.json?tenant_id={identity.tenant_id}&v={int(time.time())}"

        # package_url은 이제 템플릿 엔드포인트(template.py)에서 직접 주입하므로 여기서 계산할 필요가 없습니다.

        parameters = {
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
