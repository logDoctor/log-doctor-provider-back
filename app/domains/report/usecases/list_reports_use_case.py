from app.core.auth import Identity

from ..repository import ReportRepository
from ..schemas import ReportListResponse, ReportSchema


class ListReportsUseCase:
    def __init__(self, report_repository: ReportRepository):
        self.report_repository = report_repository

    async def execute(
        self,
        identity: Identity,
        agent_id: str,
        is_initial: bool | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> ReportListResponse:
        """조건에 맞는 리포트 목록을 조회합니다."""
        reports, next_cursor = await self.report_repository.list_reports(
            tenant_id=identity.tenant_id,
            agent_id=agent_id,
            is_initial=is_initial,
            cursor=cursor,
            limit=limit,
        )

        return ReportListResponse(
            items=[ReportSchema.model_validate(r) for r in reports],
            next_cursor=next_cursor,
        )
