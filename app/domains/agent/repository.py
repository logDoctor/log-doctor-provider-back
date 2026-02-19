from abc import ABC, abstractmethod
from datetime import datetime

# 팀의 Cosmos DB 연결 모듈
from app.infra.db.cosmos import get_container

# ---------------------------------------------------------
# 1. Interface
# ---------------------------------------------------------
class AgentRepository(ABC):
    @abstractmethod
    async def register_agent(
        self, tenant_id: str, subscription_id: str, agent_id: str, version: str
    ) -> bool:
        """에이전트를 DB에 등록합니다."""
        pass

# ---------------------------------------------------------
# 2. Mock Implementation (로컬/UI 테스트용 가짜 DB)
# ---------------------------------------------------------
class MockAgentRepository(AgentRepository):
    async def register_agent(
        self, tenant_id: str, subscription_id: str, agent_id: str, version: str
    ) -> bool:
        print(
            f"🛠️ [Mock DB] Agent Registered: Tenant={tenant_id}, Sub={subscription_id}, Agent={agent_id}, Ver={version}"
        )
        return True

# ---------------------------------------------------------
# 3. Concrete Implementation (실제 Cosmos DB용)
# ---------------------------------------------------------
class CosmosAgentRepository(AgentRepository):
    def __init__(self):
        # 'agents' 컨테이너 사용 (팀 설정에 맞게 변경 가능)
        self.container = get_container("agents")

    async def register_agent(
        self, tenant_id: str, subscription_id: str, agent_id: str, version: str
    ) -> bool:
        new_agent = {
            "id": agent_id,  # Cosmos DB의 고유 기본 키(PK)
            "tenant_id": tenant_id,
            "subscription_id": subscription_id,
            "agent_id": agent_id,
            "version": version,
            "status": "Active",
            "registered_at": datetime.now().isoformat(),
        }
        
        # DB에 저장 또는 덮어쓰기
        self.container.upsert_item(body=new_agent)
        return True