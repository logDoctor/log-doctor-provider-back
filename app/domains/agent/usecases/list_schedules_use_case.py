from app.core.auth.models import Identity
from app.core.exceptions import ForbiddenException
from app.domains.agent.models.schedule import Schedule
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.repositories import ScheduleRepository


class ListSchedulesUseCase:
    def __init__(
        self,
        schedule_repository: ScheduleRepository,
        agent_repository: AgentRepository,
    ):
        self.schedule_repository = schedule_repository
        self.agent_repository = agent_repository

    async def execute(self, identity: Identity, agent_id: str) -> list[Schedule]:
        agent = await self.agent_repository.get_by_id(identity.tenant_id, agent_id)
        if not agent or agent.tenant_id != identity.tenant_id:
            raise ForbiddenException("Agent not found or access denied.")
        return await self.schedule_repository.list_by_agent(
            identity.tenant_id, agent_id
        )
