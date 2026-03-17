import structlog

from app.core.exceptions import NotFoundException
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentResponse, ConfirmAgentDeletionResponse

logger = structlog.get_logger()


class ConfirmAgentDeletionUseCase:
    def __init__(self, agent_repository: AgentRepository):
        self.agent_repository = agent_repository

    async def execute(
        self, tenant_id: str, agent_id: str
    ) -> ConfirmAgentDeletionResponse:
        """
        Azure 리소스 그룹이 삭제된 것을 프론트엔드가 확인한 후 호출합니다.
        비즈니스 규칙 및 상태 전이는 Agent 엔티티 내부에서 처리합니다.
        """
        agent = await self.agent_repository.get_by_id(
            tenant_id=tenant_id, id=agent_id
        )
        if not agent:
            raise NotFoundException(f"Agent not found: {agent_id}")

        agent.confirm_deletion()

        await self.agent_repository.upsert_agent(agent)

        return ConfirmAgentDeletionResponse(
            message=f"Agent {agent_id} has been marked as DELETED.",
            agent=AgentResponse.model_validate(agent),
        )
