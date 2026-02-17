from fastapi import APIRouter, Depends
from fastapi_restful.cbv import cbv

from .dependencies import get_tenant_status_use_case
from .schemas import TenantResponse
from .usecases.get_tenant_status_use_case import GetTenantStatusUseCase

router = APIRouter(prefix="/tenants", tags=["Tenant"])


@cbv(router)
class TenantRouter:
    use_case: GetTenantStatusUseCase = Depends(get_tenant_status_use_case)

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
