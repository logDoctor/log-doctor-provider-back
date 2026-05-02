from fastapi import Depends, HTTPException, Query
from fastapi_restful.cbv import cbv

from app.core.auth.guards import get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import get_get_insight_use_case, get_rebuild_insight_use_case
from .schemas import InsightRebuildResponse, InsightResponse
from .usecases import GetInsightUseCase, RebuildInsightUseCase

router = APIRouter(tags=["Insight"])


@cbv(router)
class InsightRouter:
    @router.get("/", response_model=InsightResponse)
    async def get_insights(
        self,
        agent_id: str = Query(..., description="에이전트 ID"),
        period: str = Query("1w", description="조회 기간 (1d, 1w, 1m, all)"),
        identity: Identity = Depends(get_current_identity),
        use_case: GetInsightUseCase = Depends(get_get_insight_use_case),
    ):
        """지정된 에이전트의 통계 인사이트를 조회합니다."""
        result = await use_case.execute(
            identity=identity,
            agent_id=agent_id,
            period=period,
        )

        if not result:
            raise HTTPException(
                status_code=404, detail="인사이트 데이터를 찾을 수 없습니다."
            )

        return result

    @router.post("/rebuild", response_model=InsightRebuildResponse)
    async def rebuild_insights(
        self,
        agent_id: str = Query(..., description="에이전트 ID"),
        identity: Identity = Depends(get_current_identity),
        use_case: RebuildInsightUseCase = Depends(get_rebuild_insight_use_case),
    ):
        """에이전트의 인사이트 데이터를 원본 리포트 기반으로 재계산합니다."""
        count = await use_case.execute(
            identity=identity,
            agent_id=agent_id,
        )

        return InsightRebuildResponse(
            status="rebuilt",
            agent_id=agent_id,
            containers_updated=["daily", "weekly", "monthly", "total"],
            total_reports_processed=count,
        )
