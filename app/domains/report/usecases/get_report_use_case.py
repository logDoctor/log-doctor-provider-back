import asyncio
import time

from app.core.auth import Identity
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger

from ..repository import ReportRepository
from ..schemas import ReportSchema

logger = get_logger("get_report_use_case")


class GetReportUseCase:
    def __init__(self, report_repository: ReportRepository):
        self.report_repository = report_repository

    async def execute(
        self, identity: Identity, report_id: str, wait_for_completion: bool = False
    ) -> ReportSchema:
        """리포트 상세 정보를 조회합니다. wait_for_completion이 True이면 상태 변화를 대기합니다(Long-polling)."""
        report = await self.report_repository.get_by_id(identity.tenant_id, report_id)
        if not report:
            raise NotFoundException(f"Report {report_id} not found.")

        if wait_for_completion and report.is_analyzing:
            report = await self._wait_for_report_completion(identity, report_id, report)

        return ReportSchema.model_validate(report)

    async def _wait_for_report_completion(
        self, identity: Identity, report_id: str, initial_report: any
    ) -> any:
        """리포트 상태가 PENDING에서 벗어날 때까지 대기합니다 (Long-polling)."""
        max_wait_seconds = 50
        check_interval = 5
        start_time = time.time()

        logger.info(
            "long_polling_started",
            report_id=report_id,
            tenant_id=identity.tenant_id,
        )

        current_report = initial_report
        while time.time() - start_time < max_wait_seconds:
            await asyncio.sleep(check_interval)

            latest_report = await self.report_repository.get_by_id(
                identity.tenant_id, report_id
            )
            if not latest_report:
                break

            current_report = latest_report
            if not current_report.is_analyzing:
                logger.info(
                    "status_changed_during_polling",
                    report_id=report_id,
                    status=current_report.status,
                )
                return current_report

        logger.info("long_polling_timeout", report_id=report_id)
        return current_report
