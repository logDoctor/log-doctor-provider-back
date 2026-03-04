from fastapi import Depends, Query
from fastapi_restful.cbv import cbv

from app.core.auth.guards import get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import (
    get_register_tenant_use_case,
    get_search_tenant_users_use_case,
    get_tenant_status_use_case,
    get_update_tenant_use_case,
)
from .schemas import (
    GetTenantStatusResponse,
    RegisterTenantRequest,
    RegisterTenantResponse,
    UpdateTenantRequest,
)
from .usecases import (
    GetTenantStatusUseCase,
    RegisterTenantUseCase,
    SearchTenantUsersUseCase,
    UpdateTenantUseCase,
)

router = APIRouter(prefix="/tenants", tags=["Tenant"])

@cbv(router)
class TenantRouter:
    def __init__(
        self,
        get_tenant_status_use_case: GetTenantStatusUseCase = Depends(get_tenant_status_use_case),
        register_tenant_use_case: RegisterTenantUseCase = Depends(get_register_tenant_use_case),
        search_tenant_users_use_case: SearchTenantUsersUseCase = Depends(get_search_tenant_users_use_case),
        update_tenant_use_case: UpdateTenantUseCase = Depends(get_update_tenant_use_case),
    ):
        self.get_tenant_status_use_case = get_tenant_status_use_case
        self.register_tenant_use_case = register_tenant_use_case
        self.search_tenant_users_use_case = search_tenant_users_use_case
        self.update_tenant_use_case = update_tenant_use_case

    @router.get("/me", response_model=GetTenantStatusResponse)
    async def get_my_tenant_status(
        self,
        identity: Identity = Depends(get_current_identity),
    ):
        """
        사용자 자신의 테넌트 등록 상태 및 에이전트 활성화 여부를 조회합니다.
        """
        return await self.get_tenant_status_use_case.execute(identity)

    @router.patch("/me", response_model=GetTenantStatusResponse)
    async def update_my_tenant(
        self,
        request: UpdateTenantRequest,
        identity: Identity = Depends(get_current_identity),
    ):
        """
        생성된 테넌트의 정보(운영자 계정 리스트 등)를 부분 업데이트합니다.
        """
        return await self.update_tenant_use_case.execute(identity, request)

    @router.post("/", response_model=RegisterTenantResponse, status_code=201)
    async def register_tenant(
        self,
        request: RegisterTenantRequest,
        identity: Identity = Depends(get_current_identity)
    ):
        """
        SSO 헤더 정보를 바탕으로 명시적으로 테넌트를 생성(가입)합니다.
        지정된 운영자 계정 리스트(privileged_accounts)를 함께 저장합니다.
        """
        return await self.register_tenant_use_case.execute(identity, request.privileged_accounts)

    @router.get("/admins/search")
    async def search_tenant_users(
        self, 
        query: str, 
        skiptoken: str | None = Query(None, description="건너뛸 다음 페이지 토큰 (페이지네이션용)"),
        identity: Identity = Depends(get_current_identity)
    ):
        """
        테넌트 내에서 사용자를 이름이나 이메일로 검색합니다.
        """
        return await self.search_tenant_users_use_case.execute(identity, query, skiptoken)
