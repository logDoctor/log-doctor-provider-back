from app.core.auth.models import Identity
from app.core.exceptions import ForbiddenException, NotFoundException
from app.domains.agent.repositories import ScheduleRepository


class DeleteScheduleUseCase:
    def __init__(self, schedule_repository: ScheduleRepository):
        self.schedule_repository = schedule_repository

    async def execute(
        self, identity: Identity, agent_id: str, schedule_id: str
    ) -> None:
        schedule = await self.schedule_repository.get_by_id(agent_id, schedule_id)
        if not schedule:
            raise NotFoundException(f"Schedule {schedule_id} not found.")
        if schedule.tenant_id != identity.tenant_id or schedule.agent_id != agent_id:
            raise ForbiddenException("Access denied.")
        await self.schedule_repository.delete(agent_id, schedule_id)
