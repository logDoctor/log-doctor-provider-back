from abc import ABC, abstractmethod
from datetime import datetime

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.infra.db.cosmos import get_container


# 1. Abstract Interface
class TenantRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tenant_id: str) -> dict | None:
        """Fetch tenant by ID"""
        pass

    @abstractmethod
    async def create(self, tenant_id: str) -> dict:
        """Create a new tenant"""
        pass


# 2. Concrete Implementation (Cosmos DB)
class AzureTenantRepository(TenantRepository):
    def __init__(self):
        # In a real app, you might want to handle container initialization or error if it doesn't exist
        self.container = get_container("tenants")

    async def get_by_id(self, tenant_id: str) -> dict | None:
        try:
            # Cosmos DB read_item requires both id and partition key
            # Assuming tenant_id is both id and partition key for tenants container
            item = self.container.read_item(item=tenant_id, partition_key=tenant_id)
            return item
        except CosmosResourceNotFoundError:
            return None

    async def create(self, tenant_id: str) -> dict:
        new_tenant = {
            "id": tenant_id,
            "tenant_id": tenant_id,
            "is_active": False,
            "created_at": datetime.now().isoformat(),
        }
        return self.container.create_item(body=new_tenant)


# 3. User Repository Interface
class UserRepository(ABC):
    @abstractmethod
    async def get_by_oid(self, oid: str, tenant_id: str) -> dict | None:
        pass

    @abstractmethod
    async def create(self, oid: str, tenant_id: str, name: str) -> dict:
        pass


# 4. User Repository Implementation (Cosmos DB)
class AzureUserRepository(UserRepository):
    def __init__(self):
        self.container = get_container("users")

    async def get_by_oid(self, oid: str, tenant_id: str) -> dict | None:
        try:
            item = self.container.read_item(item=oid, partition_key=tenant_id)
            return item
        except CosmosResourceNotFoundError:
            return None

    async def create(self, oid: str, tenant_id: str, name: str) -> dict:
        new_user = {
            "id": oid,
            "tenant_id": tenant_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
        }
        return self.container.create_item(body=new_user)
