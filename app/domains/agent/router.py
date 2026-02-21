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

    @router.post("/webhook")
    async def mock_webhook(self, payload: dict):
        """
        [임시 테스트용] Azure Portal에서 배포된 에이전트의 첫 생존 신고(Webhook)를 받는 엔드포인트입니다.
        """
        import structlog
        logger = structlog.get_logger()
        
        logger.info(
            "🚀 [WEBHOOK 수신 성공!] Azure Agent 핑 도착",
            payload=payload,
            message="프론트엔드 버튼 -> 포탈 배포 -> 파이썬 에이전트 구동 -> 백엔드 도착까지 완벽하게 성공했습니다!"
        )
        return {"status": "success", "message": "Webhook received successfully"}
