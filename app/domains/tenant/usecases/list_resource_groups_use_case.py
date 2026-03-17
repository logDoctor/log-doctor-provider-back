from app.core.auth.models import Identity
from app.core.interfaces.azure_arm import AzureArmService


class ListResourceGroupsUseCase:
    def __init__(self, azure_arm_service: AzureArmService):
        self.azure_arm_service = azure_arm_service

    async def execute(self, identity: Identity, subscription_id: str) -> list[dict]:
        """조회 가능한 리소스 그룹 명단을 반환합니다."""
        return await self.azure_arm_service.list_resource_groups(
            access_token=identity.sso_token,
            subscription_id=subscription_id,
        )
