import logging
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentHandshakeRequest, AgentHandshakeResponse

class HandshakeAgentUseCase:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    async def execute(self, request: AgentHandshakeRequest) -> AgentHandshakeResponse:
        # 1. 요청 들어왔을 때 확인용 로그 남기기 (운영 필수)
        logging.info(f"👋 [Handshake] 에이전트 연결 요청: Tenant={request.tenant_id}, Agent={request.agent_id} (v{request.agent_version})")

        # 2. 검증 로직 (TODO: 나중에 Tenant DB 조회 로직 추가 예정)
        # TODO: Add validation logic (e.g. check if tenant exists)

        # 3. Repository를 통해 DB에 저장 (팀의 스키마 파라미터 완벽 적용)
        await self.repository.register_agent(
            tenant_id=request.tenant_id,
            subscription_id=request.subscription_id,
            agent_id=request.agent_id,
            version=request.agent_version,
        )

        # 4. 프론트엔드/에이전트에 응답 반환
        return AgentHandshakeResponse(
            success=True, 
            message="Agent handshake successful"
        )