from app.domains.tenant.repository import TenantRepository
from app.domains.tenant.schemas import TenantResponse


class TenantStatusChecker:
    def __init__(self, repository: TenantRepository):
        self.repository = repository

    async def check(self, tenant_id: str) -> TenantResponse:
        tenant_data = await self.repository.get_by_id(tenant_id)

        if not tenant_data:
            return TenantResponse(
                tenant_id=tenant_id, is_registered=False, is_agent_active=False
            )

        return TenantResponse(
            tenant_id=tenant_data["tenant_id"],
            is_registered=True,
            is_agent_active=tenant_data.get("is_active", False),
            registered_at=tenant_data.get("created_at"),
        )
