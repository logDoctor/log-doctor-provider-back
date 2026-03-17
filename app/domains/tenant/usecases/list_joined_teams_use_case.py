import structlog

from app.core.auth.services.graph_service import GraphService

logger = structlog.get_logger()

class ListJoinedTeamsUseCase:
    """사용자가 가입한 팀 목록을 조회하여 프론트엔드 설정 UI에 제공합니다."""

    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service

    async def execute(self, tenant_id: str) -> list[dict]:
        return await self.graph_service.list_joined_teams(tenant_id)
