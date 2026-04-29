import structlog

from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.exceptions import ConflictException, NotFoundException
from app.core.interfaces.azure_arm import AzureArmService
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.schemas import CheckAzureResourceGroupStatusResponse

logger = structlog.get_logger()


class CheckAzureResourceGroupStatusUseCase:
    def __init__(
        self,
        repository: AgentRepository,
        azure_arm_service: AzureArmService,
    ):
        self.repository = repository
        self.azure_arm_service = azure_arm_service

    async def execute(
        self, identity: Identity, tenant_id: str, agent_id: str
    ) -> CheckAzureResourceGroupStatusResponse:
        """Azure 리소스 그룹 존재 여부 확인 유스케이스 (Phase 2 - 읽기)

        OBO 토큰을 사용하여 사용자의 권한으로 리소스 그룹 존재 여부를 확인합니다.
        DB 상태를 변경하지 않습니다.
        """
        agent = await self.repository.get_by_id(tenant_id=tenant_id, id=agent_id)
        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found.")
        if agent.is_deleted():
            raise ConflictException(f"Agent {agent_id} is already deleted.")

        arm_token = await get_obo_access_token(identity.sso_token)

        exists = await self.azure_arm_service.check_resource_group_exists(
            access_token=arm_token,
            subscription_id=agent.subscription_id,
            resource_group_name=agent.resource_group_name,
        )

        return CheckAzureResourceGroupStatusResponse(
            exists=exists,
            resource_group_name=agent.resource_group_name,
        )
