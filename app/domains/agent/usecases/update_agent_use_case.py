from fastapi import HTTPException

from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentUpdateRequest, AgentUpdateResponse


class UpdateAgentUseCase:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    async def execute(self, request: AgentUpdateRequest) -> AgentUpdateResponse:
        agent = await self.repository.get_agent(
            tenant_id=request.tenant_id, agent_id=request.agent_id
        )

        if not agent:
            raise HTTPException(
                status_code=404, detail=f"Agent {request.agent_id} not found."
            )

        updated_fields = agent.update(
            version=request.version,
            status=request.status,
            analysis_schedule=request.analysis_schedule,
        )

        if updated_fields:
            # 업데이트된 정보 저장
            await self.repository.upsert_agent(agent.to_dict())

        return AgentUpdateResponse(
            success=True,
            message=f"Agent {request.agent_id} updated successfully.",
            updated_fields=updated_fields,
        )
