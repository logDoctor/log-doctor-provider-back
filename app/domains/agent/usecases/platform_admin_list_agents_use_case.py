from app.core.auth import Identity
from app.core.exceptions import ForbiddenException
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentResponse, PlatformAdminListAgentsResponse


class PlatformAdminListAgentsUseCase:
    """플랫폼 관리자용 에이전트 목록 조회 유스케이스.

    전체 테넌트 혹은 특정 테넌트를 지정하여 모든 에이전트를 조회할 수 있습니다.
    """

    def __init__(self, repository: AgentRepository):
        self.repository = repository

    async def execute(
        self,
        identity: Identity,
        tenant_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> PlatformAdminListAgentsResponse:
        if not identity.is_platform_admin():
            raise ForbiddenException(
                "This feature is restricted to platform administrators."
            )

        items, total = await self.repository.list_agents(
            tenant_id, skip=skip, limit=limit
        )

        return PlatformAdminListAgentsResponse(
            items=[AgentResponse.model_validate(a) for a in items],
            total_count=total,
            skip=skip,
            limit=limit,
        )
