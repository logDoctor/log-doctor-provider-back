from fastapi import Depends
from azure.cosmos.aio import ContainerProxy

# 인프라(DB 연결) 모듈
from app.infra.db.cosmos import get_container

# 에이전트 도메인 모듈
from app.domains.agent.repository import AgentRepository, CosmosAgentRepository
from app.domains.agent.usecases.agent_handshaker import AgentHandshaker

# 테넌트 도메인 모듈
from app.domains.tenant.dependencies import get_tenant_repository
from app.domains.tenant.repository import TenantRepository


def get_agent_container() -> ContainerProxy:
    return get_container("agents")


def get_agent_repository(
    container: ContainerProxy = Depends(get_agent_container),
) -> AgentRepository:
    return CosmosAgentRepository(container=container)


def get_agent_handshaker(
    agent_repo: AgentRepository = Depends(get_agent_repository),
    tenant_repo: TenantRepository = Depends(get_tenant_repository),
) -> AgentHandshaker:
    return AgentHandshaker(agent_repo=agent_repo, tenant_repo=tenant_repo)
