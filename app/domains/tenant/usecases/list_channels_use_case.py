import structlog

from app.core.auth.services.graph_service import GraphService

logger = structlog.get_logger()

class ListChannelsUseCase:
    """팀 내의 채널 목록을 조회하여 프론트엔드 설정 UI에 제공합니다."""

    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service

    async def execute(self, tenant_id: str, team_id: str) -> list[dict]:
        if not team_id:
            logger.warning("team_id is missing during channel listing", tenant_id=tenant_id)
            return []
            
        return await self.graph_service.list_channels(tenant_id, team_id)
