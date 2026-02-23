from fastapi import APIRouter, Depends
from fastapi_restful.cbv import cbv

from app.core.auth import admin_required, tenant_verified

from .dependencies import (
    get_handshake_agent_use_case,
    get_should_agent_run_use_case,
    get_trigger_agent_analysis_use_case,
    get_update_agent_use_case,
)
from .schemas import (
    AgentHandshakeRequest,
    AgentHandshakeResponse,
    AgentPollingResponse,
    AgentTriggerRequest,
    AgentTriggerResponse,
    AgentUpdateRequest,
    AgentUpdateResponse,
)
from .usecases import (
    HandshakeAgentUseCase,
    ShouldAgentRunUseCase,
    TriggerAgentAnalysisUseCase,
    UpdateAgentUseCase,
)

router = APIRouter(prefix="/agents", tags=["Agent"])


@cbv(router)
class AgentRouter:
    handshake_use_case: HandshakeAgentUseCase = Depends(get_handshake_agent_use_case)
    should_run_use_case: ShouldAgentRunUseCase = Depends(get_should_agent_run_use_case)
    trigger_use_case: TriggerAgentAnalysisUseCase = Depends(
        get_trigger_agent_analysis_use_case
    )
    update_use_case: UpdateAgentUseCase = Depends(get_update_agent_use_case)

    @router.post("/handshake", response_model=AgentHandshakeResponse)
    @tenant_verified
    async def handshake(self, request: AgentHandshakeRequest):
        """
        에이전트로부터의 최초 핸드쉐이크 요청을 처리하고 정보를 등록합니다.
        (Decorator-based Tenant Validation 적용)
        """
        return await self.handshake_use_case.execute(request)

    @router.get("/should-i-run", response_model=AgentPollingResponse)
    @tenant_verified
    async def should_i_run(self, tenant_id: str, agent_id: str):
        """
        에이전트가 주기적으로 호출하여 분석을 수행해야 하는지 확인합니다. (Polling)
        """
        return await self.should_run_use_case.execute(tenant_id, agent_id)

    @router.post("/trigger", response_model=AgentTriggerResponse)
    @admin_required
    async def trigger(self, request: AgentTriggerRequest = None):
        """
        사용자의 요청에 의해 특정 에이전트의 분석을 즉시 트리거합니다. (운영자 전용)
        """
        return await self.trigger_use_case.execute(request)

    @router.patch("/{agent_id}", response_model=AgentUpdateResponse)
    @admin_required
    async def update_agent(
        self, agent_id: str = None, request: AgentUpdateRequest = None
    ):
        """
        특정 에이전트의 정보(스케줄, 상태 등)를 변경합니다. (운영자 전용)
        """
        # 경로의 agent_id를 요청 데이터에 맞춤
        request.agent_id = agent_id
        return await self.update_use_case.execute(request)
