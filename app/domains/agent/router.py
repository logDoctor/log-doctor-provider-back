from fastapi import APIRouter, Depends
from fastapi_restful.cbv import cbv

from .dependencies import get_agent_handshaker
from .schemas import AgentHandshakeRequest, AgentHandshakeResponse
from .services import AgentHandshaker

router = APIRouter(prefix="/agents", tags=["Agent"])


@cbv(router)
class AgentRouter:
    handshaker: AgentHandshaker = Depends(get_agent_handshaker)

    @router.post("/handshake", response_model=AgentHandshakeResponse)
    async def process_agent_handshake(
        self,
        request: AgentHandshakeRequest,
    ):
        """
        에이전트 배포 완료 후 호출되는 웹훅 핸들러입니다.
        """
        return await self.handshaker.handshake(request)
