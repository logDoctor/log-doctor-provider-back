from abc import ABC, abstractmethod


# 1. Interface
class AgentRepository(ABC):
    @abstractmethod
    async def register_agent(
        self, tenant_id: str, subscription_id: str, agent_id: str, version: str
    ) -> bool:
        """에이전트를 DB에 등록합니다."""
        pass


# 2. Implementation (Mock/Cosmos)
class MockAgentRepository(AgentRepository):
    async def register_agent(
        self, tenant_id: str, subscription_id: str, agent_id: str, version: str
    ) -> bool:
        # DB Insert/Update logic here
        # For now, just print to console to simulate DB action
        print(
            f"[DB] Agent Registered: Tenant={tenant_id}, Sub={subscription_id}, Agent={agent_id}, Ver={version}"
        )
        return True
