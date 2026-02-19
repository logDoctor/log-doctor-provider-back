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
class CosmosTenantRepository(TenantRepository):
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

class MockTenantRepository(TenantRepository):
    """로컬 테스트를 위한 가짜 DB 부품입니다."""
    async def get_by_id(self, tenant_id: str) -> dict | None:
        # 가짜 테넌트 데이터를 무조건 성공하는 것처럼 돌려줍니다.
        return {
            "id": tenant_id,
            "tenant_id": tenant_id,
            "is_active": True,
            "created_at": "2026-02-19T00:00:00"
        }

    async def create(self, tenant_id: str) -> dict:
        return {"id": tenant_id, "tenant_id": tenant_id, "is_active": True}