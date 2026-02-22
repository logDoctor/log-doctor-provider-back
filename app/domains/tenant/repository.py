from abc import ABC, abstractmethod
from datetime import datetime, timezone

from azure.cosmos.exceptions import CosmosResourceNotFoundError

from app.infra.db.cosmos import get_container


# 1. Abstract Interface
class TenantRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tenant_id: str) -> dict | None:
        pass

    @abstractmethod
    async def create(self, tenant_id: str, subscription_id: str) -> dict:
        pass

    # 기존 데이터를 업데이트하는 인터페이스
    @abstractmethod
    async def update(self, tenant_data: dict) -> dict:
        pass


# 2. Concrete Implementation (Cosmos DB)
class CosmosTenantRepository(TenantRepository):
    def __init__(self):
        self.container = get_container("tenants")

    async def get_by_id(self, tenant_id: str) -> dict | None:
        try:
            item = await self.container.read_item(
                item=tenant_id, partition_key=tenant_id
            )
            return item
        except CosmosResourceNotFoundError:
            return None

    async def create(self, tenant_id: str, subscription_id: str) -> dict:
        new_tenant = {
            "id": tenant_id,
            "tenant_id": tenant_id,
            "subscription_id": subscription_id,  # 요청받은 구독 ID 저장
            "is_active": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return await self.container.upsert_item(body=new_tenant)

    # 기존 데이터를 통째로 덮어쓰는(Upsert) 기능
    async def update(self, tenant_data: dict) -> dict:
        return await self.container.upsert_item(body=tenant_data)
