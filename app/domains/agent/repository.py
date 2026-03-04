from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from .models import Agent


# 1. Interface
class AgentRepository(ABC):
    @abstractmethod
    async def get_agent(self, tenant_id: str, id: str) -> Agent | None:
        """기본키(id)로 에이전트 정보를 직접 조회합니다."""
        pass

    @abstractmethod
    async def get_active_agent_by_client_id(self, tenant_id: str, agent_id: str) -> Agent | None:
        """가장 최근 활성화된(또는 삭제 중인) 에이전트 우선으로 클라이언트 ID(agent_id) 기반 정보를 조회합니다."""
        pass

    @abstractmethod
    async def upsert_agent(self, item: dict) -> Agent:
        """에이전트 정보를 저장 또는 업데이트합니다."""
        pass

    @abstractmethod
    async def list_agents(
        self, tenant_id: str | None, skip: int = 0, limit: int = 10
    ) -> tuple[list[Agent], int]:
        """에이전트 목록과 전체 개수를 조회합니다."""
        pass


# 2. Implementation (Cosmos)
@cosmos_repository(map_to=Agent)
class AzureAgentRepository(AgentRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def get_agent(self, tenant_id: str, id: str) -> Agent | None:
        return await self.container.read_item(item=id, partition_key=tenant_id)

    async def get_active_agent_by_client_id(self, tenant_id: str, agent_id: str) -> Agent | None:
        # CosmosDB Query로 활성/가장 최근 갱신된 에이전트 1건을 가져옵니다.
        # 동일한 agent_id 중 최신 레코드(삭제되지 않은 것 우선) 1건
        query = (
            "SELECT * FROM c "
            "WHERE c.tenant_id = @tenant_id AND c.agent_id = @agent_id"
        )
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@agent_id", "value": agent_id},
        ]
        
        items = self.container.query_items(
            query=query,
            parameters=parameters,
            partition_key=tenant_id
        )
        
        results = [item async for item in items]
        if not results:
            return None
            
        # In-memory sorting: ACTIVE < DELETED, and newer _ts first
        # status ASC (ACTIVE, INITIALIZING, DEACTIVATING, DELETED, ...)
        results.sort(key=lambda x: (x.get("status", "ZZZ"), -x.get("_ts", 0)))
        
        return results[0] # Decorator will handle mapping to Agent

    async def upsert_agent(self, item: dict) -> Agent:
        return await self.container.upsert_item(item)

    async def list_agents(
        self, tenant_id: str | None, skip: int = 0, limit: int = 10
    ) -> tuple[list[Agent], int]:
        # 1. 기본 쿼리 및 파라미터 설정
        where_clauses = ["c.status != 'DELETED'"]
        parameters = []

        if tenant_id:
            where_clauses.append("c.tenant_id = @tenant_id")
            parameters.append({"name": "@tenant_id", "value": tenant_id})

        where_clause = "WHERE " + " AND ".join(where_clauses)

        # 2. 전체 개수 조회
        count_query = f"SELECT VALUE COUNT(1) FROM c {where_clause}"
        count_result = self.container.query_items(
            query=count_query,
            parameters=parameters,
            partition_key=tenant_id if tenant_id else None,
        )
        total_count = 0
        async for item in count_result:
            total_count = item
            break

        # 3. 데이터 조회 (Pagination)
        data_query = (
            f"SELECT * FROM c {where_clause} OFFSET {skip} LIMIT {limit}"
        )
        items = self.container.query_items(
            query=data_query,
            parameters=parameters,
            partition_key=tenant_id if tenant_id else None,
        )
        agents = [Agent.from_dict(item) async for item in items]

        return agents, total_count
