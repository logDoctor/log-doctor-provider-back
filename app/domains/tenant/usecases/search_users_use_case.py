from app.core.exceptions import UnauthorizedException
from app.core.auth.services.graph_service import GraphService
from app.core.auth.models import Identity

class SearchTenantUsersUseCase:
    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service

    async def execute(self, identity: Identity, query: str, skiptoken: str | None = None) -> dict:
        return await self.graph_service.search_users(identity.tenant_id, query, skiptoken)
