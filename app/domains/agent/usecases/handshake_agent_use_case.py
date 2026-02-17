from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentHandshakeRequest, AgentHandshakeResponse


class HandshakeAgentUseCase:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    async def execute(self, request: AgentHandshakeRequest) -> AgentHandshakeResponse:
        # TODO: Add validation logic (e.g. check if tenant exists)

        await self.repository.register_agent(
            tenant_id=request.tenant_id,
            subscription_id=request.subscription_id,
            agent_id=request.agent_id,
            version=request.agent_version,
        )

        return AgentHandshakeResponse(
            success=True, message="Agent handshake successful"
        )
