from fastapi import APIRouter, Depends
from fastapi_restful.cbv import cbv

from .dependencies import get_status_checker
from .schemas import TenantResponse
from .services import TenantStatusChecker

router = APIRouter(prefix="/tenants", tags=["Tenant"])


@cbv(router)
class TenantRouter:
    # Service is injected via Depends in the class attribute
    checker: TenantStatusChecker = Depends(get_status_checker)

    @router.get("/me", response_model=TenantResponse)
    async def check_my_tenant_status(
        self,
        # TODO: Extract from SSO Token
        tenant_id: str = "mock-tenant-id",
    ):
        """
        사용자 자신의 테넌트 등록 상태 및 에이전트 활성화 여부를 조회합니다.
        """
        return await self.checker.check(tenant_id)
