import httpx
import structlog
from app.core.auth.models import Identity
from app.core.auth.services.graph_service import GraphService

logger = structlog.get_logger()

class GetTeamDetailUseCase:
    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service

    async def execute(self, identity: Identity, team_id: str) -> dict:
        """
        특정 팀의 상세 정보와 우리 앱의 설치 여부를 조회합니다.
        """
        # 1. 설치 여부 확인
        is_installed = await self.graph_service.check_app_installation_status(
            identity.tenant_id, team_id, sso_token=identity.sso_token
        )
        
        # 2. 팀 기본 정보 조회 (Graph API)
        team_info = {"id": team_id, "name": "Unknown Team", "is_installed": is_installed}
        
        try:
            # 봇 토큰이나 사용자 토큰 중 하나로 팀 이름을 가져오기 위해 시도
            # (여기서는 단순화를 위해 설치 여부 위주로 처리하고, 필요 시 Graph API로 이름 조회 가능)
            pass 
        except Exception as e:
            logger.warning(f"Failed to fetch team details for {team_id}", error=str(e))

        return team_info
