import uuid

from app.core.auth import Identity
from app.core.exceptions import (
    ForbiddenException,
    InternalServerException,
    NotFoundException,
)
from app.core.interfaces.azure_queue import AzureQueueService
from app.core.logging import get_logger
from app.domains.agent.constants import AGENT_COMMAND_QUEUE_NAME, COMMAND_RUN_ANALYSIS
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentCommandMessage

from ..models import Report
from ..repository import ReportRepository
from ..schemas import CreateReportRequest, CreateReportResponse, ReportSchema

logger = get_logger("create_report_use_case")


class CreateReportUseCase:
    def __init__(
        self,
        report_repository: ReportRepository,
        agent_repository: AgentRepository,
        azure_queue_service: AzureQueueService,
    ):
        self.report_repository = report_repository
        self.agent_repository = agent_repository
        self.azure_queue_service = azure_queue_service

    async def execute(
        self,
        identity: Identity,
        request: CreateReportRequest,
    ) -> CreateReportResponse:
        """새로운 리포트 생성을 요청하고 에이전트에 분석 명령을 전달합니다."""
        agent = await self.agent_repository.get_by_id(
            identity.tenant_id, request.agent_id
        )
        if not agent:
            raise NotFoundException(f"Agent {request.agent_id} not found.")

        if not agent.can_start_analysis():
            raise ForbiddenException(
                f"Cannot start analysis for agent in status: {agent.status.value}"
            )

        storage_account_name = agent.get_storage_account_name()
        if not storage_account_name:
            raise InternalServerException("Agent storage configuration is missing.")

        trace_id = str(uuid.uuid4())
        params = self._generate_request_params(request)

        report = Report.create(
            tenant_id=identity.tenant_id,
            agent_id=request.agent_id,
            trace_id=trace_id,
            triggered_by=identity.email or identity.id or "unknown",
            level=request.level,
            request_params=params,
        )

        queue_message = AgentCommandMessage(
            agent_id=request.agent_id,
            command=COMMAND_RUN_ANALYSIS,
            params={**params, "level": request.level},
            trace_id=trace_id,
        )

        try:
            await self.azure_queue_service.push(
                account_name=storage_account_name,
                queue_name=AGENT_COMMAND_QUEUE_NAME,
                message=queue_message.model_dump(),
            )
        except Exception as e:
            report.mark_as_failed(f"Queue delivery failed: {str(e)}")
            await self.report_repository.create_report(report)
            raise InternalServerException(
                f"Failed to send analysis command: {str(e)}"
            ) from e

        try:
            await self.report_repository.create_report(report)
        except Exception as e:
            logger.error(
                "report_db_save_failed_after_queue_success",
                error=str(e),
                trace_id=trace_id,
            )
            raise InternalServerException(
                f"Analysis command sent but failed to record report in database. (TraceID: {trace_id})"
            ) from e

        return CreateReportResponse(
            message=f"Analysis report requested successfully. (ID: {report.id})",
            report=ReportSchema.model_validate(report),
        )

    def _generate_request_params(self, request):
        request_params = {}

        if request.start_time:
            request_params["start_time"] = request.start_time
        if request.end_time:
            request_params["end_time"] = request.end_time

        return request_params
