from fastapi import APIRouter, Depends
from fastapi_restful.cbv import cbv

from .dependencies import get_agent_handshaker
from .schemas import AgentHandshakeRequest, AgentHandshakeResponse
from .usecases.agent_handshaker import AgentHandshaker

router = APIRouter(prefix="/agents", tags=["Agent"])


@cbv(router)
class AgentRouter:
    handshaker: AgentHandshaker = Depends(get_agent_handshaker)

    @router.post("/handshake", response_model=AgentHandshakeResponse)
    async def handshake(self, request: AgentHandshakeRequest):
        """
        에이전트로부터의 최초 핸드쉐이크 요청을 처리하고 정보를 등록
        (유효한 테넌트인지 검증하고, 정보를 저장한 뒤 테넌트를 활성화)
        """
        return await self.handshaker.execute(request)
