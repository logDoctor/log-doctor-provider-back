import structlog
from app.domains.tenant.repository import TenantRepository
from app.domains.tenant.schemas import TenantResponse, TenantOnboardRequest

logger = structlog.get_logger()


# NounVerber 룰 적용
class TenantOnboarder:
    def __init__(self, repository: TenantRepository):
        self.repository = repository

    async def execute(self, request: TenantOnboardRequest) -> TenantResponse:
        logger.info(
            f"[온보딩] 테넌트 가입 요청 수신 (Tenant: {request.tenant_id}, Sub: {request.subscription_id})"
        )

        # 1. 실제 DB(Cosmos)에 생성
        tenant_data = await self.repository.create(
            tenant_id=request.tenant_id, subscription_id=request.subscription_id
        )

        logger.info(
            "[온보딩] Cosmos DB 저장 완료 및 응답 반환", tenant_id=request.tenant_id
        )

        return TenantResponse(
            tenant_id=tenant_data["tenant_id"],
            is_registered=True,
            is_agent_active=tenant_data.get("is_active", False),
            registered_at=tenant_data.get("created_at"),
        )
