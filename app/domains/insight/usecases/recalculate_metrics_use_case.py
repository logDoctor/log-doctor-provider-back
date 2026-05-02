from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.domains.report.repositories import ReportRepository

from ..constants import KST
from ..models import PeriodType
from ..repositories.insight import InsightRepository

logger = get_logger("recalculate_metrics_use_case")


class RecalculateMetricsUseCase:
    """진단 해결 시 최신 리포트의 요약을 바탕으로 인사이트를 재계산합니다."""

    def __init__(
        self, insight_repository: InsightRepository, report_repository: ReportRepository
    ):
        self.insight_repository = insight_repository
        self.report_repository = report_repository

    async def execute(self, tenant_id: str, agent_id: str, report_id: str) -> None:
        """지정된 리포트의 요약을 바탕으로 현재 인사이트 스냅샷을 동기화합니다."""
        # 1. 원본 리포트 조회 (이미 summary가 갱신되어 있어야 함)
        report = await self.report_repository.get_by_id(tenant_id, report_id)
        if not report or not report.summary:
            logger.warning("report_not_found_or_summary_missing", report_id=report_id)
            return

        now_kst = datetime.now(KST)

        # 2. 4개 기간에 대해 현재 기간 키 계산 및 업데이트 수행
        periods = [
            (PeriodType.DAILY, now_kst.strftime("%Y-%m-%d")),
            (PeriodType.WEEKLY, now_kst.strftime("%G-W%V")),
            (PeriodType.MONTHLY, now_kst.strftime("%Y-%m")),
            (PeriodType.TOTAL, "total"),
        ]

        for period_type, period_key in periods:
            await self._update_if_latest(
                tenant_id, agent_id, period_type, period_key, report
            )

        logger.info("insight_recalculation_completed", agent_id=agent_id, report_id=report_id)

    async def _update_if_latest(
        self,
        tenant_id: str,
        agent_id: str,
        period_type: PeriodType,
        period_key: str,
        report: Any,
    ):
        """해당 리포트가 인사이트의 최신 리포트인 경우에만 스냅샷 정보를 갱신합니다."""
        insight = await self.insight_repository.get_by_id(
            tenant_id, agent_id, period_type, period_key
        )
        if not insight:
            return

        # 이 리포트가 해당 인사이트 문서에 기록된 마지막 리포트인 경우에만 
        # (즉, 현재 대시보드에 표시 중인 스냅샷의 원본인 경우에만) 해결 상태를 반영합니다.
        if insight.latest_report_id == report.id:
            summary = report.summary
            # 활성 리스크 = 탐지된 진단 수 - 해결된 진단 수
            insight.active_risks_count = max(
                0,
                summary.get("detected_diagnosis_count", 0)
                - summary.get("resolved_diagnosis_count", 0),
            )
            # 총 해결 수도 요약 기준으로 동기화
            insight.total_resolved = summary.get("resolved_diagnosis_count", 0)

            insight.last_updated_at = datetime.utcnow().isoformat()
            await self.insight_repository.upsert(insight)
            logger.debug(
                "insight_snapshot_updated",
                period=period_type,
                active_risks=insight.active_risks_count,
            )
