from fastapi import APIRouter, Depends
from fastapi_restful.cbv import cbv

from .dependencies import get_handshake_agent_use_case
from .schemas import AgentHandshakeRequest, AgentHandshakeResponse
from .usecases.handshake_agent_use_case import HandshakeAgentUseCase

router = APIRouter(prefix="/agents", tags=["Agent"])


@cbv(router)
class AgentRouter:
    use_case: HandshakeAgentUseCase = Depends(get_handshake_agent_use_case)

    @router.post("/handshake", response_model=AgentHandshakeResponse)
    async def handshake(self, request: AgentHandshakeRequest):
        """
        에이전트로부터의 최초 핸드쉐이크 요청을 처리하고 정보를 등록합니다.
        """
        return await self.use_case.execute(request)
