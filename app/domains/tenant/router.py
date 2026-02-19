from fastapi import APIRouter, Depends, Header
from fastapi_restful.cbv import cbv

from .dependencies import (
    get_tenant_status_use_case,
    get_subscriptions_use_case,
    get_onboard_tenant_use_case,  # 1. 온보딩 조립 라인 추가
)
from .schemas import (
    TenantResponse,
    GetSubscriptionsResponse,
    TenantOnboardRequest,  # 2. 온보딩 요청 데이터 양식 추가
)
from .usecases.get_tenant_status_use_case import GetTenantStatusUseCase
from .usecases.get_subscriptions_use_case import GetSubscriptionsUseCase
from .usecases.onboard_tenant_use_case import (
    OnboardTenantUseCase,
)  # 3. 온보딩 두뇌 추가

router = APIRouter(prefix="/tenants", tags=["Tenant"])


@cbv(router)
class TenantRouter:
    # 1. 기존 유즈케이스 (상태 조회용)
    status_use_case: GetTenantStatusUseCase = Depends(get_tenant_status_use_case)

    # 2. 신규 유즈케이스 (구독 조회용)
    subscriptions_use_case: GetSubscriptionsUseCase = Depends(
        get_subscriptions_use_case
    )

    # 3. 온보딩 유즈케이스
    onboard_use_case: OnboardTenantUseCase = Depends(get_onboard_tenant_use_case)

    @router.get("/me", response_model=TenantResponse)
    async def check_my_tenant_status(
        self,
        # TODO: Extract from SSO Token
        tenant_id: str = "mock-tenant-id",
    ):
        """
        사용자 자신의 테넌트 등록 상태 및 에이전트 활성화 여부를 조회합니다.
        """
        return await self.status_use_case.execute(tenant_id)

    # ==========================================
    # 신규 API 1: 프론트엔드가 호출할 구독 목록 조회
    # ==========================================
    @router.get("/subscriptions", response_model=GetSubscriptionsResponse)
    async def get_my_subscriptions(
        self,
        authorization: str = Header(
            default="Bearer mock-sso-token-1234",
            description="프론트엔드에서 넘어온 SSO 토큰",
        ),
    ):
        """
        [OBO Flow] 사용자의 SSO 토큰을 이용해 Azure에서 접근 가능한 구독 목록을 조회합니다.
        """
        sso_token = (
            authorization.replace("Bearer ", "")
            if authorization.startswith("Bearer ")
            else authorization
        )
        return await self.subscriptions_use_case.execute(sso_token)

    # ==========================================
    # 신규 API 2: 프론트엔드가 호출할 테넌트 온보딩(생성)
    # ==========================================
    @router.post("/", response_model=TenantResponse)
    async def onboard_tenant(self, request: TenantOnboardRequest):
        """
        [Step 3] 사용자가 선택한 구독 정보로 새로운 테넌트를 온보딩(등록)합니다.
        """
        return await self.onboard_use_case.execute(request)
