from abc import ABC, abstractmethod
from datetime import datetime, timezone

import structlog
from azure.cosmos.aio import ContainerProxy
from azure.cosmos.exceptions import CosmosHttpResponseError

from app.core.exceptions import LogDoctorException

logger = structlog.get_logger()


# ---------------------------------------------------------
# 1. Interface
# ---------------------------------------------------------
class AgentRepository(ABC):
    @abstractmethod
    async def register_agent(
        self,
        tenant_id: str,
        subscription_id: str,
        agent_id: str,
        agent_version: str,
        hostname: str,
    ) -> bool:
        """에이전트를 DB에 등록합니다."""
        pass


# ---------------------------------------------------------
# 2. Mock Implementation (로컬 테스트용)
# ---------------------------------------------------------
class MockAgentRepository(AgentRepository):
    async def register_agent(
        self,
        tenant_id: str,
        subscription_id: str,
        agent_id: str,
        agent_version: str,
        hostname: str,
    ) -> bool:
        logger.info(
            f"🛠️ [Mock DB] Agent Registered: Tenant={tenant_id}, Sub={subscription_id}, Agent={agent_id}, Ver={agent_version}"
        )
        return True


# ---------------------------------------------------------
# 3. Concrete Implementation (실제 Cosmos DB용)
# ---------------------------------------------------------
class CosmosAgentRepository(AgentRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def register_agent(
        self,
        tenant_id: str,
        subscription_id: str,
        agent_id: str,
        agent_version: str,
        hostname: str,
    ) -> bool:
        new_agent = {
            "id": agent_id,  # Cosmos DB의 고유 기본 키(PK)
            "tenant_id": tenant_id,  # Partition Key
            "subscription_id": subscription_id,
            "agent_id": agent_id,
            "agent_version": agent_version,
            "hostname": hostname,
            "status": "Active",
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # 비동기로 Cosmos DB에 덮어쓰기(Upsert)
            await self.container.upsert_item(body=new_agent)
            return True
        except CosmosHttpResponseError as e:
            logger.error("❌ Cosmos DB 에이전트 저장 실패", error=str(e))
            raise LogDoctorException(
                status_code=500, detail="Failed to save agent to database"
            )
