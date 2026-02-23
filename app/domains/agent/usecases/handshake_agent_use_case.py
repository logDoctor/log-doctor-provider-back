from fastapi import HTTPException

from app.domains.agent.models import Agent
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentHandshakeRequest, AgentHandshakeResponse
from app.domains.tenant.repository import TenantRepository


class HandshakeAgentUseCase:
    def __init__(
        self, repository: AgentRepository, tenant_repository: TenantRepository
    ):
        self.repository = repository
        self.tenant_repository = tenant_repository

    async def execute(self, request: AgentHandshakeRequest) -> AgentHandshakeResponse:
        # 1. 테넌트 존재 여부 확인
        # (AOP 레이어에서 Token tid와 request.tenant_id 일치 여부는 이미 검증됨)
        tenant = await self.tenant_repository.get_by_id(request.tenant_id)
        if tenant is None:
            raise HTTPException(
                status_code=404, detail=f"Tenant {request.tenant_id} not found"
            )

        agent = await self.repository.get_agent(
            tenant_id=request.tenant_id, agent_id=request.agent_id
        )
        if agent and agent.is_same_version(request.agent_version):
            return AgentHandshakeResponse(
                success=True,
                message=f"Agent {request.agent_id} (v{request.agent_version}) is already registered",
            )

        if agent:
            agent.update_version(request.agent_version)
        else:
            agent = Agent.create(
                tenant_id=request.tenant_id,
                subscription_id=request.subscription_id,
                agent_id=request.agent_id,
                version=request.agent_version,
            )

        result = await self.repository.upsert_agent(agent.to_dict())
        if not result:
            raise HTTPException(
                status_code=500, detail="Failed to persist agent handshake"
            )

        return AgentHandshakeResponse(
            success=True,
            message=f"Agent {result.agent_id} (v{result.version}) successfully (Status: {result.status})",
        )
