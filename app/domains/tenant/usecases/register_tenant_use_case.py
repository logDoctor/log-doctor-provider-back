from app.core.auth.models import Identity
from app.core.exceptions import ConflictException
from app.domains.tenant.models import Tenant
from app.domains.tenant.repository import TenantRepository
from app.domains.tenant.schemas import TenantResponse


class RegisterTenantUseCase:
    """
    프론트엔드에서 SSO 인증 성공 후 테넌트 등록을 명시적으로 요청(POST /tenants)할 때 사용됩니다.
    토큰에서 추출한 Tenant ID(tid)를 DB에 upsert합니다.
    """

    def __init__(self, repository: TenantRepository):
        self.repository = repository

    async def execute(self, identity: Identity) -> TenantResponse:
        tid = identity.tenant_id

        if not tid:
            raise ValueError("No Tenant ID (tid) found in the provided token.")

        tenant_record = await self.repository.get_by_id(tid)

        if tenant_record:
            raise ConflictException(f"Tenant with ID '{tid}' is already registered.")

        tenant_record = Tenant.create(tid)
        saved_tenant = await self.repository.upsert(tenant_record)

        return TenantResponse(
            tenant_id=saved_tenant.tenant_id,
            is_registered=True,
            is_agent_active=saved_tenant.is_active,
            registered_at=saved_tenant.created_at,
        )
