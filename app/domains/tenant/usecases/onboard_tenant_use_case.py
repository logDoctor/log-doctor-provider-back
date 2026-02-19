import logging
from app.domains.tenant.repository import TenantRepository
from app.domains.tenant.schemas import TenantResponse, TenantOnboardRequest


class OnboardTenantUseCase:
    # 이번에는 Azure가 아니라 우리 '내부 DB(Repository)' 부품을 주입받습니다.
    def __init__(self, repository: TenantRepository):
        self.repository = repository

    async def execute(self, request: TenantOnboardRequest) -> TenantResponse:
        logging.info(
            f"[온보딩] 테넌트 가입 요청 수신 (Tenant: {request.tenant_id}, Sub: {request.subscription_id})"
        )

        # 1. DB(지금은 Mock)에 테넌트 정보를 생성(Create)합니다.
        # (기존 repository 초안에 만들어져 있던 create 함수를 그대로 씁니다!)
        tenant_data = await self.repository.create(request.tenant_id)

        logging.info("[온보딩] DB 저장 완료 및 응답 반환")

        # 2. 결과를 깔끔하게 TenantResponse 모델로 포장해서 돌려줍니다.
        return TenantResponse(
            tenant_id=tenant_data["tenant_id"],
            is_registered=True,
            is_agent_active=tenant_data.get("is_active", False),
            registered_at=tenant_data.get("created_at"),
        )
