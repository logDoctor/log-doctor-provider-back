import structlog

from app.core.exceptions import LogDoctorException
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentHandshakeRequest, AgentHandshakeResponse
from app.domains.tenant.repository import TenantRepository

logger = structlog.get_logger()


class AgentHandshaker:
    # TODO 해결: TenantRepository를 추가로 주입받아 Cross-Domain 검증 로직을 수행
    def __init__(self, agent_repo: AgentRepository, tenant_repo: TenantRepository):
        self.agent_repo = agent_repo
        self.tenant_repo = tenant_repo

    async def execute(self, request: AgentHandshakeRequest) -> AgentHandshakeResponse:
        # 1. 확인용 로그 남기기 (structlog 적용)
        logger.info(
            "👋 [Handshake] 에이전트 연결 요청",
            tenant_id=request.tenant_id,
            agent_id=request.agent_id,
            version=request.agent_version,
        )

        # 2. 검증 로직 (TODO 해결)
        tenant_data = await self.tenant_repo.read_item(
            request.tenant_id, request.tenant_id
        )

        if not tenant_data:
            logger.warning(
                "❌ [Handshake] 유효하지 않은 테넌트", tenant_id=request.tenant_id
            )
            raise LogDoctorException(
                status_code=404, detail="Tenant not found. Please onboard first."
            )

        # 3. Repository를 통해 DB에 저장 (hostname 등 최신 스키마 반영)
        await self.agent_repo.register_agent(
            tenant_id=request.tenant_id,
            subscription_id=request.subscription_id,
            agent_id=request.agent_id,
            agent_version=request.agent_version,
            hostname=request.hostname,
        )

        # 4. 테넌트 상태 업데이트 (최초 연결 시 활성화)
        if not tenant_data.get("is_active"):
            tenant_data["is_active"] = True
            await self.tenant_repo.upsert_item(tenant_data)
            logger.info(
                "✨ [Handshake] 테넌트 상태 활성화 (is_active=True) 완료",
                tenant_id=request.tenant_id,
            )

        # 5. 프론트엔드/에이전트에 응답 반환
        return AgentHandshakeResponse(
            success=True, message="Agent handshake successful and tenant activated."
        )
