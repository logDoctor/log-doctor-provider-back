from datetime import datetime
from typing import Any, Dict, List

from app.core.logging import get_logger
from app.domains.report.models import Report

from ..constants import KST
from ..models import InsightDocument, InsightEngineItem, InsightTrendItem, PeriodType
from ..repositories.insight import InsightRepository

logger = get_logger("update_insight_use_case")


class UpdateInsightUseCase:
    def __init__(self, insight_repository: InsightRepository):
        self.insight_repository = insight_repository

    async def execute(self, tenant_id: str, agent_id: str, report: Report) -> None:
        """리포트 완료 시 4개 기간 인사이트를 증분 업데이트합니다."""
        summary = report.summary
        if not summary:
            logger.warning("report_summary_missing", report_id=report.id)
            return

        now_kst = datetime.now(KST)

        # 4개 기간 키 계산
        period_keys = {
            PeriodType.DAILY: now_kst.strftime("%Y-%m-%d"),
            PeriodType.WEEKLY: now_kst.strftime("%G-W%V"),  # ISO 주차 (월요일 시작)
            PeriodType.MONTHLY: now_kst.strftime("%Y-%m"),
            PeriodType.TOTAL: "total",
        }

        for period_type, period_key in period_keys.items():
            try:
                await self._update_period_insight(
                    tenant_id, agent_id, period_type, period_key, report, now_kst
                )
            except Exception as e:
                logger.error(
                    "failed_to_update_period_insight",
                    agent_id=agent_id,
                    period=period_type,
                    error=str(e),
                )
                # 한 기간 실패가 다른 기간에 영향을 주지 않도록 계속 진행

    async def _update_period_insight(
        self,
        tenant_id: str,
        agent_id: str,
        period_type: PeriodType,
        period_key: str,
        report: Report,
        now_kst: datetime,
    ):
        summary = report.summary
        insight = await self.insight_repository.get_by_id(
            tenant_id, agent_id, period_type, period_key
        )

        if not insight:
            insight = InsightDocument(
                id=f"{agent_id}:{period_key}"
                if period_type != PeriodType.TOTAL
                else agent_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                period_type=period_type,
                period_key=period_key,
            )

        # 1. 누적 메트릭 증분
        insight.total_reports += 1
        insight.total_detected += summary.get("detected_diagnosis_count", 0)
        insight.total_resolved += summary.get("resolved_diagnosis_count", 0)
        insight.total_healthy += summary.get("healthy_diagnosis_count", 0)

        # 2. 스냅샷 메트릭 (항상 최신 리포트 기준으로 덮어쓰기)
        insight.active_risks_count = max(
            0,
            summary.get("detected_diagnosis_count", 0)
            - summary.get("resolved_diagnosis_count", 0),
        )
        insight.latest_report_id = report.id

        # 3. 트렌드 데이터 업데이트
        trend_label = self._get_trend_label(now_kst, period_type)
        self._update_trend(insight.trend, trend_label, summary)

        # 4. 엔진 분포 (최신 리포트 기준)
        # TODO: 리포트에서 직접 가져오거나 진단 항목 조회 로직 필요 (현재는 summary에서 간단히 추출)
        # 우선 설계 문서대로 summary에 포함된 resource_groups 정보를 활용하거나 기본값으로 설정
        insight.engine_distribution = self._calculate_engine_dist(summary)

        insight.last_updated_at = datetime.utcnow().isoformat()
        await self.insight_repository.upsert(insight)

    def _get_trend_label(self, dt: datetime, period_type: PeriodType) -> str:
        if period_type == PeriodType.DAILY:
            return dt.strftime("%H:00")
        elif period_type == PeriodType.WEEKLY:
            days = ["월", "화", "수", "목", "금", "토", "일"]
            return f"{dt.month}/{dt.day} {days[dt.weekday()]}"
        elif period_type == PeriodType.MONTHLY:
            return f"{dt.month}/{dt.day}"
        else:  # TOTAL
            return dt.strftime("%Y-%m")

    def _update_trend(
        self, trend: List[InsightTrendItem], label: str, summary: Dict[str, Any]
    ):
        # 동일 라벨이 있으면 더함 (예: 같은 시간에 진단이 두 번 완료된 경우)
        for item in trend:
            if item.label == label:
                item.detected += summary.get("detected_diagnosis_count", 0)
                item.resolved += summary.get("resolved_diagnosis_count", 0)
                return

        # 없으면 추가
        trend.append(
            InsightTrendItem(
                label=label,
                detected=summary.get("detected_diagnosis_count", 0),
                resolved=summary.get("resolved_diagnosis_count", 0),
            )
        )

        # 정렬 및 크기 제한 (Daily=24, Weekly=7, Monthly=31 등)
        # 여기서는 단순 추가만 하고, 리포지토리에서 조회 시 기간에 맞게 정리할 수도 있음

    def _calculate_engine_dist(
        self, summary: Dict[str, Any]
    ) -> List[InsightEngineItem]:
        """리포트 요약의 리소스 그룹 정보를 바탕으로 엔진별 분포를 계산합니다."""
        # 기본 엔진 맵
        engine_counts = {"DET": 0, "PRV": 0, "FLT": 0, "RET": 0}

        # 리소스 그룹 이름에서 엔진 코드를 유추 (규칙 기반)
        # 예: 'Detector' -> DET, 'Prevention' -> PRV 등
        rgs = summary.get("resource_groups", [])
        for rg in rgs:
            name = rg.get("name", "").upper()
            if "DETECTOR" in name:
                engine_counts["DET"] += 1
            elif "PREVENTION" in name:
                engine_counts["PRV"] += 1
            elif "FILTER" in name:
                engine_counts["FLT"] += 1
            elif "RETENTION" in name:
                engine_counts["RET"] += 1

        return [
            InsightEngineItem(engine_code=code, count=count)
            for code, count in engine_counts.items()
        ]
