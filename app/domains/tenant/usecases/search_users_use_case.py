from app.core.auth.models import Identity
from app.core.auth.services.graph_service import GraphService


class SearchTenantUsersUseCase:
    def __init__(self, graph_service: GraphService):
        self.graph_service = graph_service

    async def execute(self, identity: Identity, query: str, skiptoken: str | None = None) -> dict:
        return await self.graph_service.search_users(identity.tenant_id, query, skiptoken)
