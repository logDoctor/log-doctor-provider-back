from datetime import UTC, datetime

from app.core.auth.models import Identity
from app.core.cron import CronHelper
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.core.interfaces.azure_arm import AzureArmService
from app.core.logging import get_logger
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.repositories import ScheduleRepository
from app.domains.agent.schemas.schedule import UpdateScheduleRequest

logger = get_logger("update_schedule_use_case")


class UpdateScheduleUseCase:
    def __init__(
        self,
        schedule_repository: ScheduleRepository,
        agent_repository: AgentRepository,
        azure_arm_service: AzureArmService,
    ):
        self.schedule_repository = schedule_repository
        self.agent_repository = agent_repository
        self.azure_arm_service = azure_arm_service

    async def execute(
        self,
        identity: Identity,
        agent_id: str,
        schedule_id: str,
        request: UpdateScheduleRequest,
    ):
        schedule = await self.schedule_repository.get_by_id(agent_id, schedule_id)
        if not schedule:
            raise NotFoundException(f"Schedule {schedule_id} not found.")
        if schedule.tenant_id != identity.tenant_id or schedule.agent_id != agent_id:
            raise ForbiddenException("Access denied.")

        if request.enabled is not None:
            schedule.enabled = request.enabled
        if request.language is not None:
            schedule.language = request.language

        cron_changed = request.cron_expression is not None
        tz_changed = request.timezone is not None

        if request.cron_expression is not None:
            schedule.cron_expression = request.cron_expression
        if request.timezone is not None:
            schedule.timezone = request.timezone

        if cron_changed or tz_changed:
            now_utc = datetime.now(UTC)
            next_run = CronHelper.get_next_run(
                schedule.cron_expression, now_utc, schedule.timezone
            )
            schedule.next_run_at = next_run.isoformat()

        if request.configurations is not None:
            agent = await self.agent_repository.get_by_id(
                identity.tenant_id, schedule.agent_id
            )
            all_rg_ids = set()
            for config in request.configurations:
                if config.resource_groups:
                    for rg in config.resource_groups:
                        rg_id = (
                            rg.get("id")
                            if isinstance(rg, dict)
                            else getattr(rg, "id", None)
                        )
                        if rg_id:
                            all_rg_ids.add(rg_id)

            if all_rg_ids and agent:
                try:
                    valid_rgs = await self.azure_arm_service.list_resource_groups(
                        access_token=identity.sso_token,
                        subscription_id=agent.subscription_id,
                    )
                    valid_ids = {rg["id"] for rg in valid_rgs}
                    for rg_id in all_rg_ids:
                        if rg_id not in valid_ids:
                            raise BadRequestException(
                                f"Invalid resource group ID: {rg_id}"
                            )
                except BadRequestException:
                    raise
                except Exception as e:
                    logger.warning("rg_validation_skipped", error=str(e))

            schedule.configurations = [c.model_dump() for c in request.configurations]

        schedule.updated_at = datetime.now(UTC).isoformat()
        return await self.schedule_repository.update(schedule)
