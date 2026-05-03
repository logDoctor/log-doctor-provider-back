import asyncio
from typing import Any

from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.domains.notification.service import NotificationService
from app.domains.report.models import ReportStatus
from app.domains.report.repositories import DiagnosisRepository, ReportRepository

logger = get_logger("update_report_status_use_case")


# TODO: 리팩토링 필요
class UpdateReportStatusUseCase:
    """리포트의 상태(Status)를 업데이트하는 UseCase"""

    def __init__(
        self,
        report_repository: ReportRepository,
        diagnosis_repository: DiagnosisRepository,
        notification_service: NotificationService,
        insight_publisher: Any = None,  # DI를 위해 추가
    ):
        self.report_repository = report_repository
        self.diagnosis_repository = diagnosis_repository
        self.notification_service = notification_service
        self.insight_publisher = insight_publisher

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

        calculated_summary = None
        if status == ReportStatus.COMPLETED:
            diagnoses = await self.diagnosis_repository.list_by_report(
                tenant_id, report_id
            )
            total = len(diagnoses)

            def get_val(d, key, default):
                return (
                    d.get(key, default)
                    if isinstance(d, dict)
                    else getattr(d, key, default)
                )

            detected = sum(
                1 for d in diagnoses if get_val(d, "status", "").upper() == "DETECTED"
            )
            healthy = sum(
                1 for d in diagnoses if get_val(d, "status", "").upper() == "HEALTHY"
            )
            undiagnosed = sum(
                1 for d in diagnoses if get_val(d, "status", "").upper() == "UNDIAGNOSED"
            )
            resolved = sum(1 for d in diagnoses if get_val(d, "is_resolved", False))

            rgs = {}  # {lower_name: {"id": id, "name": original_name}}
            for d in diagnoses:
                rg_dict = get_val(d, "resource_group", None)
                if isinstance(rg_dict, dict) and "name" in rg_dict:
                    name = rg_dict["name"]
                    lower_name = name.lower()
                    if lower_name not in rgs:
                        rgs[lower_name] = {"id": rg_dict.get("id", ""), "name": name}

            calculated_summary = {
                "total_diagnosis_count": total,
                "resolved_diagnosis_count": resolved,
                "detected_diagnosis_count": detected,
                "healthy_diagnosis_count": healthy,
                "undiagnosed_diagnosis_count": undiagnosed,
                "resource_groups": [
                    {"id": info["id"], "name": info["name"]} for info in rgs.values()
                ],
            }

        updated_fields = report.update(
            status=status, error=error, summary=calculated_summary
        )

        if updated_fields:
            await self.report_repository.update_report(report)

            if "status" in updated_fields and report.status == ReportStatus.COMPLETED:
                try:
                    asyncio.create_task(
                        self.notification_service.notify_analysis_completed(
                            tenant_id=report.tenant_id,
                            report_id=report.id,
                            summary="detailed_diagnosis_results_available",
                            agent_id=report.agent_id,
                            language=report.request_params.get("language")
                            if report.request_params
                            else "ko",
                        )
                    )
                    logger.info(
                        "triggering_notification",
                        report_id=report.id,
                        language=report.request_params.get("language")
                        if report.request_params
                        else "MISSING",
                    )
                except Exception as e:
                    logger.error(
                        "failed_to_trigger_notification",
                        report_id=report.id,
                        error=str(e),
                    )

            if (
                "status" in updated_fields
                and report.status == ReportStatus.COMPLETED
                and self.insight_publisher
            ):
                    try:
                        asyncio.create_task(
                            self.insight_publisher.publish(
                                event_type="report_completed",
                                tenant_id=report.tenant_id,
                                agent_id=report.agent_id,
                                report_id=report.id,
                            )
                        )
                    except Exception as e:
                        logger.error(
                            "failed_to_publish_insight_event",
                            report_id=report.id,
                            error=str(e),
                        )
