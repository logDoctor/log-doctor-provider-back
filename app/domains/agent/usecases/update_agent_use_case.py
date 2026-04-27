import structlog

from app.core.exceptions import ConflictException, NotFoundException
from app.core.auth.models import Identity
from app.core.auth.services.graph_service import GraphService
from app.domains.agent.models import AgentStatus
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentResponse, UpdateAgentResponse

logger = structlog.get_logger()


class UpdateAgentUseCase:
    """에이전트 속성 업데이트 유스케이스 예: 알림 채널 분리)"""

    def __init__(self, agent_repository: AgentRepository, graph_service: GraphService):
        self.agent_repository = agent_repository
        self.graph_service = graph_service

    async def execute(
        self,
        identity: Identity,
        tenant_id: str,
        agent_id: str,
        teams_info: dict | None = None,
        status: str | None = None,
    ) -> UpdateAgentResponse:
        agent = await self.agent_repository.get_by_id(tenant_id=tenant_id, id=agent_id)
        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found.")
        if agent.is_deleted():
            raise ConflictException(f"Cannot update a deleted agent: {agent_id}")

        agent_status = AgentStatus(status) if status else None

        if agent_status == AgentStatus.ACTIVE:
            agent.restore_to_active()

        if teams_info:
            new_team_id = teams_info.get("team_id")
            
            if new_team_id:
                # [AUTO-INSTALL] 저장 시점에 항상 봇 설치 상태를 확인하여 Roster 누락 방지
                await self.graph_service.ensure_app_installed_in_team(
                    tenant_id=tenant_id,
                    team_id=new_team_id,
                    sso_token=identity.sso_token
                )
        
        agent.update(teams_info=teams_info, status=agent_status)

        await self.agent_repository.upsert_agent(agent)

        return UpdateAgentResponse(
            message=f"Agent {agent_id} updated successfully.",
            agent=AgentResponse.model_validate(agent),
        )
