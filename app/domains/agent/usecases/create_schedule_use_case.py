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
from app.domains.agent.models.schedule import Schedule
from app.domains.agent.repositories import AgentRepository, ScheduleRepository
from app.domains.agent.schemas.schedule import CreateScheduleRequest
from app.domains.package.repository import AgentPackageRepository

logger = get_logger("create_schedule_use_case")

FREE_SCHEDULE_LIMIT = 1


class CreateScheduleUseCase:
    def __init__(
        self,
        schedule_repository: ScheduleRepository,
        agent_repository: AgentRepository,
        azure_arm_service: AzureArmService,
        package_repository: AgentPackageRepository,
    ):
        self.schedule_repository = schedule_repository
        self.agent_repository = agent_repository
        self.azure_arm_service = azure_arm_service
        self.package_repository = package_repository

    async def execute(
        self, identity: Identity, agent_id: str, request: CreateScheduleRequest
    ) -> Schedule:
        agent = await self.agent_repository.get_by_id(identity.tenant_id, agent_id)
        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found.")
        if agent.tenant_id != identity.tenant_id:
            raise ForbiddenException("Access denied to this agent.")

        # 🚀 [NEW] 메이저 버전 체크 (업데이트 강제 정책) - 스케줄 관리 차단
        latest_pkg = await self.package_repository.get_by_version("latest")
        if latest_pkg and agent.version:
            agent_major = int(agent.version.split(".")[0]) if "." in agent.version else 0
            latest_major = int(latest_pkg.version.split(".")[0]) if "." in latest_pkg.version else 0
            
            if agent_major < latest_major:
                raise ForbiddenException(
                    f"Agent version {agent.version} is outdated. Major update to {latest_pkg.version} is required before managing schedules."
                )

        count = await self.schedule_repository.count_by_agent(
            identity.tenant_id, agent_id
        )
        if count >= FREE_SCHEDULE_LIMIT:
            raise ForbiddenException(
                f"Free plan allows {FREE_SCHEDULE_LIMIT} schedule(s) per agent. "
                "Upgrade your plan to add more schedules."
            )

        # RG 검증 (생성 시 1회, 이후 실행 시에는 스냅샷 신뢰)
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

        if all_rg_ids:
            try:
                valid_rgs = await self.azure_arm_service.list_resource_groups(
                    access_token=identity.sso_token,
                    subscription_id=agent.subscription_id,
                )
                valid_ids = {rg["id"] for rg in valid_rgs}
                for rg_id in all_rg_ids:
                    if rg_id not in valid_ids:
                        raise BadRequestException(f"Invalid resource group ID: {rg_id}")
            except BadRequestException:
                raise
            except Exception as e:
                logger.warning(
                    "rg_validation_skipped",
                    error=str(e),
                    agent_id=agent_id,
                )

        now_utc = datetime.now(UTC)
        next_run = CronHelper.get_next_run(
            request.cron_expression, now_utc, request.timezone
        )

        configurations = [c.model_dump() for c in request.configurations]

        schedule = Schedule.create(
            tenant_id=identity.tenant_id,
            agent_id=agent_id,
            enabled=request.enabled,
            cron_expression=request.cron_expression,
            timezone=request.timezone,
            language=request.language,
            configurations=configurations,
            next_run_at=next_run.isoformat(),
            created_by=identity.email or identity.id or "unknown",
        )

        return await self.schedule_repository.create(schedule)
