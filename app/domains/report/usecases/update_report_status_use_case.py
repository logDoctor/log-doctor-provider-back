from app.core.exceptions import NotFoundException
from app.domains.notification.service import NotificationService
from app.domains.report.models import ReportStatus
from app.domains.report.repository import ReportRepository


class UpdateReportStatusUseCase:
    """리포트의 상태(Status)를 업데이트하는 UseCase"""

    def __init__(
        self,
        report_repository: ReportRepository,
        notification_service: NotificationService,
    ):
        self.report_repository = report_repository
        self.notification_service = notification_service

    async def execute(
        self,
        report_id: str,
        tenant_id: str,
        status: ReportStatus | None = None,
        error: str | None = None,
    ) -> None:
        report = await self.report_repository.get_by_id(tenant_id, report_id)
        if not report:
            raise NotFoundException(f"Report not found: {report_id}")

        updated_fields = report.update(status=status, error=error)

        if updated_fields:
            await self.report_repository.update_report(report)

            # if "status" in updated_fields and report.status == ReportStatus.COMPLETED:
            #     await self.notification_service.notify_analysis_completed(
            #         tenant_id=report.tenant_id,
            #         report_id=report.id,
            #         summary="Detailed diagnosis results available.",
            #     )
