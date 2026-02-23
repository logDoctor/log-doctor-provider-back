from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from .models import Agent


# 1. Interface
class AgentRepository(ABC):
    @abstractmethod
    async def get_agent(self, tenant_id: str, agent_id: str) -> Agent | None:
        """에이전트 정보를 조회합니다."""
        pass

    @abstractmethod
    async def upsert_agent(self, item: dict) -> Agent:
        """에이전트 정보를 저장 또는 업데이트합니다."""
        pass


# 2. Implementation (Cosmos)
@cosmos_repository(map_to=Agent)
class AzureAgentRepository(AgentRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def get_agent(self, tenant_id: str, agent_id: str) -> Agent | None:
        item_id = f"{tenant_id}:{agent_id}"
        return await self.container.read_item(item=item_id, partition_key=tenant_id)

    async def upsert_agent(self, item: dict) -> Agent:
        return await self.container.upsert_item(item)
