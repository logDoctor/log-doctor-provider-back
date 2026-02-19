from fastapi import APIRouter, Depends, Header
from fastapi_restful.cbv import cbv

# --- 기존 Import 및 신규 Import 합치기 ---
from .dependencies import get_tenant_status_use_case, get_subscriptions_use_case
from .schemas import TenantResponse, GetSubscriptionsResponse
from .usecases.get_tenant_status_use_case import GetTenantStatusUseCase
from .usecases.get_subscriptions_use_case import GetSubscriptionsUseCase

router = APIRouter(prefix="/tenants", tags=["Tenant"])


@cbv(router)
class TenantRouter:
    # 1. 기존 유즈케이스 (구분을 위해서 이름만 status_use_case로 살짝 바꿨습니다!)
    status_use_case: GetTenantStatusUseCase = Depends(get_tenant_status_use_case)
    
    # 2. 🌟 신규 유즈케이스 (우리가 방금 만든 구독 조회용 두뇌!)
    subscriptions_use_case: GetSubscriptionsUseCase = Depends(get_subscriptions_use_case)

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
    # 🌟 신규 API: 프론트엔드가 호출할 구독 목록 조회
    # ==========================================
    @router.get("/subscriptions", response_model=GetSubscriptionsResponse)
    async def get_my_subscriptions(
        self,
        # 프론트엔드는 주로 Authorization 헤더에 "Bearer <토큰>" 형태로 토큰을 담아 보냅니다.
        authorization: str = Header(default="Bearer mock-sso-token-1234", description="프론트엔드에서 넘어온 SSO 토큰"),
    ):
        """
        [OBO Flow] 사용자의 SSO 토큰을 이용해 Azure에서 접근 가능한 구독 목록을 조회합니다.
        """
        # "Bearer " 글자가 붙어있으면 떼어내고 순수한 토큰 글자만 추출합니다.
        sso_token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization
        
        # 유즈케이스 실행!
        return await self.subscriptions_use_case.execute(sso_token)