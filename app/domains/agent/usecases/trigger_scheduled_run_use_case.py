import uuid
from datetime import UTC, datetime

from azure.cosmos.exceptions import CosmosAccessConditionFailedError

from app.core.cron import CronHelper
from app.core.interfaces.azure_queue import AzureQueueService
from app.core.logging import get_logger
from app.domains.agent.constants import AGENT_COMMAND_QUEUE_NAME, COMMAND_RUN_ANALYSIS
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.repositories import ScheduleRepository
from app.domains.agent.schemas import AgentCommandMessage
from app.domains.agent.schemas.schedule import TriggerScheduledRunResponse
from app.domains.report.models import Report
from app.domains.report.repositories import ReportRepository

logger = get_logger("trigger_scheduled_run_use_case")


class TriggerScheduledRunUseCase:
    """
    에이전트 타이머 폴링 시 실행 시각이 된 스케줄을 찾아 진단을 트리거합니다.

    연산 순서 (R1 설계 결정):
      1. Schedule ETag 업데이트 (중복 실행 방지 잠금)
      2. Report 생성 → Cosmos 저장
      3. Queue push
    """

    def __init__(
        self,
        schedule_repository: ScheduleRepository,
        report_repository: ReportRepository,
        agent_repository: AgentRepository,
        azure_queue_service: AzureQueueService,
    ):
        self.schedule_repository = schedule_repository
        self.report_repository = report_repository
        self.agent_repository = agent_repository
        self.azure_queue_service = azure_queue_service

    async def execute(
        self, tenant_id: str, agent_id: str
    ) -> TriggerScheduledRunResponse:
        agent = await self.agent_repository.get_by_id(tenant_id, agent_id)
        if not agent or not agent.can_start_analysis():
            return TriggerScheduledRunResponse(triggered=False)

        storage_account_name = agent.get_storage_account_name()
        if not storage_account_name:
            logger.warning("missing_storage_account", agent_id=agent_id)
            return TriggerScheduledRunResponse(triggered=False)

        schedules = await self.schedule_repository.get_enabled_by_agent(
            tenant_id, agent_id
        )
        now_utc = datetime.now(UTC)

        for schedule in schedules:
            is_due = self._is_due(schedule, now_utc)
            if not is_due:
                continue

            # 1. Schedule ETag 잠금 (중복 방지 먼저)
            next_run = CronHelper.get_next_run(
                schedule.cron_expression, now_utc, schedule.timezone
            )
            schedule.update_last_run_at(now_utc)
            schedule.update_next_run_at(next_run)
            try:
                await self.schedule_repository.update(schedule)
            except CosmosAccessConditionFailedError:
                # 다른 레플리카가 이미 이 스케줄을 선점함
                logger.info(
                    "schedule_already_claimed",
                    schedule_id=schedule.id,
                    agent_id=agent_id,
                )
                continue

            # 2. Report 생성 → Cosmos 저장
            trace_id = str(uuid.uuid4())
            report = Report.create(
                tenant_id=tenant_id,
                agent_id=agent_id,
                trace_id=trace_id,
                triggered_by=f"scheduled:{schedule.id}",
                request_params={
                    "configurations": schedule.configurations,
                    "language": schedule.language,
                },
            )
            try:
                await self.report_repository.create_report(report)
            except Exception as e:
                logger.error(
                    "report_create_failed_after_schedule_lock",
                    schedule_id=schedule.id,
                    error=str(e),
                )
                # 스케줄 잠금은 이미 업데이트됨 → 이 사이클 누락 허용 (중복 실행보다 낫다)
                continue

            # 3. Queue push
            queue_message = AgentCommandMessage(
                agent_id=agent_id,
                command=COMMAND_RUN_ANALYSIS,
                params={
                    "configurations": schedule.configurations,
                    "language": schedule.language,
                },
                trace_id=trace_id,
                report_id=report.id,
            )
            try:
                await self.azure_queue_service.push(
                    account_name=storage_account_name,
                    queue_name=AGENT_COMMAND_QUEUE_NAME,
                    message=queue_message.model_dump(),
                    tenant_id=tenant_id,
                )
            except Exception as e:
                report.mark_as_failed(f"Queue delivery failed: {str(e)}")
                await self.report_repository.update_report(report)
                logger.error(
                    "schedule_queue_push_failed",
                    schedule_id=schedule.id,
                    report_id=report.id,
                    error=str(e),
                )
                continue

            logger.info(
                "scheduled_run_triggered",
                schedule_id=schedule.id,
                report_id=report.id,
                agent_id=agent_id,
            )
            return TriggerScheduledRunResponse(
                triggered=True,
                report_id=report.id,
                schedule_id=schedule.id,
                configurations=schedule.configurations,
                language=schedule.language,
            )

        return TriggerScheduledRunResponse(triggered=False)

    def _is_due(self, schedule, now_utc: datetime) -> bool:
        if not schedule.last_run_at:
            return True
        try:
            last_run = datetime.fromisoformat(schedule.last_run_at)
            return CronHelper.is_time_to_run(
                schedule.cron_expression, last_run, now_utc, schedule.timezone
            )
        except Exception:
            return False
