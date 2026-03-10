import structlog

from app.core.auth.models import Identity
from app.core.exceptions import NotFoundException
from app.core.interfaces.azure_arm import AzureArmService
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentResponse, DeactivateAgentResponse

logger = structlog.get_logger()


class DeactivateAgentUseCase:
    """에이전트 비활성화 요청 유스케이스 (Phase 7 - 쓰기)

    Agent 엔티티의 상태를 DEACTIVATING으로 변경하고,
    Azure 리소스 그룹 삭제를 시작합니다.
    """

    def __init__(
        self,
        agent_repository: AgentRepository,
        azure_arm_service: AzureArmService,
    ):
        self.agent_repository = agent_repository
        self.azure_arm_service = azure_arm_service

    async def execute(
        self, identity: Identity, agent_id: str
    ) -> DeactivateAgentResponse:
        agent = await self.agent_repository.get_active_agent_by_client_id(
            tenant_id=identity.tenant_id, agent_id=agent_id
        )
        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found.")

        agent.deactivate()

        try:
            await self.azure_arm_service.delete_resource_group(
                access_token=identity.sso_token,
                subscription_id=agent.subscription_id,
                resource_group_name=agent.resource_group_name,
            )
        except Exception as e:
            logger.error(
                "Failed to delete Azure resource group", agent_id=agent_id, error=str(e)
            )
            agent.mark_deactivate_failed()

        await self.agent_repository.upsert_agent(agent.to_dict())

        return DeactivateAgentResponse(
            message=f"Deactivation request for agent {agent_id} is in progress.",
            agent=AgentResponse.model_validate(agent),
        )
