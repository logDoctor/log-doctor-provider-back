import uuid

from app.core.auth import Identity
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    InternalServerException,
    NotFoundException,
)
from app.core.interfaces.azure_arm import AzureArmService
from app.core.interfaces.azure_queue import AzureQueueService
from app.core.logging import get_logger
from app.domains.agent.constants import AGENT_COMMAND_QUEUE_NAME, COMMAND_RUN_ANALYSIS
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.schemas import AgentCommandMessage

from ..models import Report, ReportStatus
from ..repositories import ReportRepository
from ..schemas import CreateReportRequest, CreateReportResponse, ReportSchema

logger = get_logger("create_report_use_case")


class CreateReportUseCase:
    def __init__(
        self,
        report_repository: ReportRepository,
        agent_repository: AgentRepository,
        azure_queue_service: AzureQueueService,
        azure_arm_service: AzureArmService,
    ):
        self.report_repository = report_repository
        self.agent_repository = agent_repository
        self.azure_queue_service = azure_queue_service
        self.azure_arm_service = azure_arm_service

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

        # 0. 리소스 그룹 사전 검증 (configurations 내 모든 RGs 수집)
        request_rgs = []
        for config in request.configurations:
            if config.resource_groups:
                request_rgs.extend(config.resource_groups)

        if request_rgs:
            valid_rgs = await self.azure_arm_service.list_resource_groups(
                access_token=identity.sso_token, subscription_id=agent.subscription_id
            )
            valid_ids = {rg["id"] for rg in valid_rgs}
            for rg_item in request_rgs:
                if rg_item.id not in valid_ids:
                    raise BadRequestException(
                        f"Invalid resource group ID: {rg_item.id}"
                    )

        trace_id = str(uuid.uuid4())
        params = self._generate_request_params(request)

        existing_initial = await self.report_repository.get_initial(
            tenant_id=identity.tenant_id,
            agent_id=request.agent_id,
        )
        is_initial = self._should_be_initial(existing_initial)

        # 수신받은 configurations 명세를 그대로 스냅샷화 (Pydantic -> dict)
        configurations = [c.model_dump() for c in request.configurations]
        params["configurations"] = configurations

        report = Report.create(
            tenant_id=identity.tenant_id,
            agent_id=request.agent_id,
            trace_id=trace_id,
            triggered_by=identity.email or identity.id or "unknown",
            is_initial=is_initial,
            request_params=params,
        )

        queue_message = AgentCommandMessage(
            agent_id=request.agent_id,
            command=COMMAND_RUN_ANALYSIS,
            params={**params, "configurations": configurations},
            trace_id=trace_id,
            report_id=report.id,
        )

        try:
            await self.azure_queue_service.push(
                account_name=storage_account_name,
                queue_name=AGENT_COMMAND_QUEUE_NAME,
                message=queue_message.model_dump(),
                tenant_id=identity.tenant_id,
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
        if request.language:
            request_params["language"] = request.language
        return request_params

    def _should_be_initial(self, existing_initial: Report | None) -> bool:
        """기존 초진 리포트 유무 및 상태를 기반으로 새 리포트의 초진 여부를 결정합니다."""
        if not existing_initial:
            return True

        # 이미 존재하지만 FAILED인 경우에만 다시 초진 가능
        return existing_initial.status == ReportStatus.FAILED
