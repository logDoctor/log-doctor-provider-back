from fastapi import APIRouter, Depends
from fastapi_restful.cbv import cbv

from app.core.auth import get_current_identity
from app.core.auth.models import Identity

from .dependencies import get_register_tenant_use_case, get_tenant_status_use_case
from .schemas import TenantResponse
from .usecases import GetTenantStatusUseCase, RegisterTenantUseCase

router = APIRouter(prefix="/tenants", tags=["Tenant"])


@cbv(router)
class TenantRouter:
    use_case: GetTenantStatusUseCase = Depends(get_tenant_status_use_case)
    register_use_case: RegisterTenantUseCase = Depends(get_register_tenant_use_case)

    @router.post("/", response_model=TenantResponse)
    async def register_tenant(self, identity: Identity = Depends(get_current_identity)):
        """
        SSO 헤더 정보를 바탕으로 명시적으로 테넌트를 생성(가입)합니다.
        """
        return await self.register_use_case.execute(identity)

    @router.get("/me", response_model=TenantResponse)
    async def check_my_tenant_status(
        self,
        # TODO: Extract from SSO Token
        tenant_id: str = "mock-tenant-id",
    ):
        """
        사용자 자신의 테넌트 등록 상태 및 에이전트 활성화 여부를 조회합니다.
        """
        return await self.use_case.execute(tenant_id)
