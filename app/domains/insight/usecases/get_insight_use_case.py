from datetime import datetime, timedelta
from typing import Optional

from app.core.auth.models import Identity

from ..constants import KST
from ..models import InsightDocument, PeriodType
from ..repositories.insight import InsightRepository
from ..schemas import InsightEngineItemSchema, InsightResponse, InsightTrendItemSchema


class GetInsightUseCase:
    def __init__(self, insight_repository: InsightRepository):
        self.insight_repository = insight_repository

    async def execute(
        self, identity: Identity, agent_id: str, period: str
    ) -> Optional[InsightResponse]:
        # period 파라미터를 PeriodType으로 변환 (1d -> daily 등)
        period_map = {
            "1d": PeriodType.DAILY,
            "1w": PeriodType.WEEKLY,
            "1m": PeriodType.MONTHLY,
            "all": PeriodType.TOTAL,
        }

        period_type = period_map.get(period)
        if not period_type:
            return None

        # 현재 기준 기간 키 계산 (최신 데이터를 가져오기 위함)
        now_kst = datetime.now(KST)
        period_key = self._get_period_key(now_kst, period_type)

        insight = await self.insight_repository.get_by_id(
            identity.tenant_id, agent_id, period_type, period_key
        )
        if not insight:
            # 데이터가 없는 경우 기본 빈 인사이트 객체 생성 (404 방지)
            insight = InsightDocument(
                id=f"{agent_id}:{period_type}:{period_key}",
                tenant_id=identity.tenant_id,
                agent_id=agent_id,
                period_type=period_type,
                period_key=period_key,
            )

        # 응답 스키마로 변환
        return InsightResponse(
            period=period,
            period_label=self._get_period_label(now_kst, period_type),
            health_score=self._calculate_health_score(insight),
            active_risks_count=insight.active_risks_count,
            total_reports=insight.total_reports,
            total_detected=insight.total_detected,
            total_resolved=insight.total_resolved,
            trend=[
                InsightTrendItemSchema(
                    label=t.label, detected=t.detected, resolved=t.resolved
                )
                for t in insight.trend
            ],
            engine_distribution=[
                InsightEngineItemSchema(
                    engine_code=e.engine_code,
                    label=self._get_engine_label(e.engine_code),
                    count=e.count,
                )
                for e in insight.engine_distribution
            ],
            last_updated_at=insight.last_updated_at,
        )

    def _get_period_key(self, dt: datetime, period_type: PeriodType) -> str:
        if period_type == PeriodType.DAILY:
            return dt.strftime("%Y-%m-%d")
        elif period_type == PeriodType.WEEKLY:
            return dt.strftime("%G-W%V")
        elif period_type == PeriodType.MONTHLY:
            return dt.strftime("%Y-%m")
        else:
            return "total"

    def _get_period_label(self, dt: datetime, period_type: PeriodType) -> str:
        if period_type == PeriodType.DAILY:
            return dt.strftime("%Y년 %m월 %d일")
        elif period_type == PeriodType.WEEKLY:
            # 주 시작일(월요일)과 종료일(일요일) 계산
            start = dt - timedelta(days=dt.weekday())
            end = start + timedelta(days=6)
            return f"{start.strftime('%m/%d')} ~ {end.strftime('%m/%d')}"
        elif period_type == PeriodType.MONTHLY:
            return dt.strftime("%Y년 %m월")
        else:
            return "전체 기간"

    def _calculate_health_score(self, insight: InsightDocument) -> int:
        if insight.total_detected == 0:
            return 100
        return round(insight.total_resolved / insight.total_detected * 100)

    def _get_engine_label(self, code: str) -> str:
        labels = {"DET": "탐지", "PRV": "예방", "FLT": "필터", "RET": "보존"}
        return labels.get(code, code)
