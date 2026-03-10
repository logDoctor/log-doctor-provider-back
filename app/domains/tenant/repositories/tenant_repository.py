from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from ..models import Tenant


class TenantRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tenant_id: str) -> Tenant | None:
        """Fetch tenant by ID. Returns None if not found."""
        pass

    @abstractmethod
    async def upsert(self, tenant: Tenant) -> Tenant:
        """Upsert tenant to the database."""
        pass


@cosmos_repository(map_to=Tenant)
class AzureTenantRepository(TenantRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def get_by_id(self, tenant_id: str) -> Tenant | None:
        return await self.container.read_item(item=tenant_id, partition_key=tenant_id)

    async def upsert(self, tenant: Tenant) -> Tenant:
        return await self.container.upsert_item(body=tenant.to_dict())
