import structlog

from app.core.exceptions import ConflictException, NotFoundException
from app.domains.agent.models import AgentStatus
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentResponse, UpdateAgentResponse

logger = structlog.get_logger()


class UpdateAgentUseCase:
    """에이전트 속성 업데이트 유스케이스 예: 알림 채널 분리)"""

    def __init__(self, agent_repository: AgentRepository):
        self.agent_repository = agent_repository

    async def execute(
        self,
        tenant_id: str,
        agent_id: str,
        teams_info: dict | None = None,
        status: str | None = None,
    ) -> UpdateAgentResponse:
        agent = await self.agent_repository.get_by_id(tenant_id=tenant_id, id=agent_id)
        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found.")
        if agent.is_deleted():
            raise ConflictException(f"Cannot update a deleted agent: {agent_id}")

        agent_status = AgentStatus(status) if status else None

        if agent_status == AgentStatus.ACTIVE:
            agent.restore_to_active()

        agent.update(teams_info=teams_info, status=agent_status)

        await self.agent_repository.upsert_agent(agent)

        return UpdateAgentResponse(
            message=f"Agent {agent_id} updated successfully.",
            agent=AgentResponse.model_validate(agent),
        )
