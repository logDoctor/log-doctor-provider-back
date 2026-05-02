from app.core.auth.models import Identity
from app.core.logging import get_logger
from app.domains.report.repositories import ReportRepository

from ..models import PeriodType
from ..repositories.insight import InsightRepository
from ..usecases.update_insight_use_case import UpdateInsightUseCase

logger = get_logger("rebuild_insight_use_case")


class RebuildInsightUseCase:
    def __init__(
        self,
        insight_repository: InsightRepository,
        report_repository: ReportRepository,
        update_insight_use_case: UpdateInsightUseCase,
    ):
        self.insight_repository = insight_repository
        self.report_repository = report_repository
        self.update_insight_use_case = update_insight_use_case

    async def execute(self, identity: Identity, agent_id: str) -> int:
        """에이전트의 모든 리포트를 조회하여 인사이트를 처음부터 다시 구축합니다."""
        tenant_id = identity.tenant_id
        
        # 1. 모든 리포트 조회 (재구축을 위해 넉넉하게 100개까지 조회)
        reports, _ = await self.report_repository.list_reports(
            tenant_id=tenant_id, 
            agent_id=agent_id,
            limit=100
        )
        completed_reports = [r for r in reports if r.status == "COMPLETED"]

        # 날짜순 정렬 (증분 업데이트를 순차적으로 적용하기 위함)
        completed_reports.sort(key=lambda x: x.created_at)

        count = 0
        for report in completed_reports:
            await self.update_insight_use_case.execute(tenant_id, agent_id, report)
            count += 1

        logger.info("insight_rebuild_completed", agent_id=agent_id, count=count)
        return count
