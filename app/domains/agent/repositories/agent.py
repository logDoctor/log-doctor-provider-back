from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from ..models import Agent, AgentStatus


# 1. Interface
class AgentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tenant_id: str, id: str) -> Agent | None:
        """기본키(id)로 에이전트 정보를 직접 조회합니다."""
        pass

    @abstractmethod
    async def get_active_agent_by_client_id(
        self, tenant_id: str, agent_id: str
    ) -> Agent | None:
        """가장 최근 활성화된(또는 삭제 중인) 에이전트 우선으로 클라이언트 ID(agent_id) 기반 정보를 조회합니다."""
        pass

    @abstractmethod
    async def upsert_agent(self, agent: Agent) -> Agent:
        """에이전트 정보를 저장 또는 업데이트합니다."""
        pass

    @abstractmethod
    async def get_all_by_tenant_id(self, tenant_id: str) -> list[Agent]:
        """특정 테넌트의 모든 활성 에이전트 목록을 조회합니다."""
        pass

    @abstractmethod
    async def list_agents(
        self,
        tenant_id: str | None,
        subscription_ids: list[str] | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[Agent], int]:
        """에이전트 목록과 전체 개수를 조회합니다."""
        pass

    @abstractmethod
    async def get_agent_by_subscription(
        self, subscription_id: str, statuses: list[AgentStatus] | None = None
    ) -> Agent | None:
        """특정 구독에서 에이전트 1건을 조회합니다. (여러 상태 필터 선택 가능)"""
        pass


# 2. Implementation (Cosmos)
@cosmos_repository(map_to=Agent)
class AzureAgentRepository(AgentRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def get_by_id(self, tenant_id: str, id: str) -> Agent | None:
        return await self.container.read_item(item=id, partition_key=tenant_id)

    async def get_active_agent_by_client_id(
        self, tenant_id: str, agent_id: str
    ) -> Agent | None:
        # CosmosDB Query로 활성/가장 최근 갱신된 에이전트 1건을 가져옵니다.
        # 동일한 agent_id 중 최신 레코드(삭제되지 않은 것 우선) 1건
        query = (
            "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.agent_id = @agent_id"
        )
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@agent_id", "value": agent_id},
        ]

        items = self.container.query_items(
            query=query, parameters=parameters, partition_key=tenant_id
        )

        results = [item async for item in items]
        if not results:
            return None

        # Priority-based sorting:
        # 1. ACTIVE, INITIALIZING, DEACTIVATING, DEACTIVATE_FAILED (Alive states)
        # 2. DELETED (Dead state)
        # Within the same category, newer _ts first.
        def sort_key(x):
            status = x.get("status", AgentStatus.UNKNOWN.value)
            # Alive states get priority 0, DELETED gets priority 1
            priority = 1 if status == AgentStatus.DELETED.value else 0
            # Tie-break with status priority if needed, then timestamp
            status_map = {
                AgentStatus.ACTIVE.value: 0,
                AgentStatus.INITIALIZING.value: 1,
                AgentStatus.DEACTIVATING.value: 2,
                AgentStatus.DEACTIVATE_FAILED.value: 3,
            }
            sub_priority = status_map.get(status, 9)
            return (priority, sub_priority, -x.get("_ts", 0))

        results.sort(key=sort_key)

        return results[0]  # Decorator will handle mapping to Agent

    async def upsert_agent(self, agent: Agent) -> Agent:
        return await self.container.upsert_item(agent.to_dict())

    async def get_all_by_tenant_id(self, tenant_id: str) -> list[Agent]:
        query = (
            "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.status != @deleted"
        )
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@deleted", "value": AgentStatus.DELETED.value},
        ]
        items = self.container.query_items(
            query=query, parameters=parameters, partition_key=tenant_id
        )
        return [Agent.from_dict(item) async for item in items]

    async def list_agents(
        self,
        tenant_id: str | None,
        subscription_ids: list[str] | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[Agent], int]:
        # 1. 기본 쿼리 및 파라미터 설정
        where_clauses = [f"c.status != '{AgentStatus.DELETED.value}'"]
        parameters = []

        if tenant_id:
            where_clauses.append("c.tenant_id = @tenant_id")
            parameters.append({"name": "@tenant_id", "value": tenant_id})

        if subscription_ids:
            # IN (@sub1, @sub2, ...) 형태의 쿼리 생성
            sub_params = []
            for i, sub_id in enumerate(subscription_ids):
                param_name = f"@sub_id_{i}"
                sub_params.append(param_name)
                parameters.append({"name": param_name, "value": sub_id})

            if sub_params:
                where_clauses.append(f"c.subscription_id IN ({', '.join(sub_params)})")

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
        data_query = f"SELECT * FROM c {where_clause} ORDER BY c._ts DESC OFFSET {skip} LIMIT {limit}"
        items = self.container.query_items(
            query=data_query,
            parameters=parameters,
            partition_key=tenant_id if tenant_id else None,
        )
        agents = [Agent.from_dict(item) async for item in items]

        return agents, total_count

    async def get_agent_by_subscription(
        self, subscription_id: str, statuses: list[AgentStatus] | None = None
    ) -> Agent | None:
        query = "SELECT * FROM c WHERE c.subscription_id = @sub_id"
        parameters = [
            {"name": "@sub_id", "value": subscription_id},
        ]

        if statuses:
            status_params = []
            for i, status in enumerate(statuses):
                param_name = f"@status_{i}"
                status_params.append(param_name)
                parameters.append({"name": param_name, "value": status.value})

            query += f" AND c.status IN ({', '.join(status_params)})"

        # 구독 기반 조회는 테넌트(PartitionKey)에 관계없이 수행해야 하므로 cross-partition query 사용
        items = self.container.query_items(
            query=query, parameters=parameters, enable_cross_partition_query=True
        )
        async for item in items:
            return Agent.from_dict(item)
        return None
