from app.core.auth.models import Identity
from app.core.auth.services.auth_provider import TokenProvider
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.domains.tenant.repository import TenantRepository
from app.domains.tenant.schemas import GetTenantStatusResponse


class GetTenantStatusUseCase:
    def __init__(self, tenant_repository: TenantRepository, token_provider: TokenProvider):
        self.tenant_repository = tenant_repository
        self.token_provider = token_provider

    async def execute(self, identity: Identity) -> GetTenantStatusResponse:
        tenant_id = identity.tenant_id
        
        # 🛡️ 핵심: OBO 토큰 교환을 시도하여 실제 권한동의가 되었는지 확인합니다.
        # 이 과정에서 권한이 없으면 UnauthorizedException(401/403)이 발생하며 전역 핸들러가 처리합니다.
        await self.token_provider.get_obo_token(identity.sso_token)

        tenantEntity = await self.tenant_repository.get_by_id(tenant_id)
        
        if not tenantEntity:
            has_privileged_role = identity.is_global_admin or (identity.roles and len(identity.roles) > 0)
            if not has_privileged_role:
                raise UnauthorizedException(
                    "NOT_ASSIGNED|ACCESS_DENIED|로그닥터 앱을 사용할 권한이 없습니다. "
                    "조직 관리자에게 문의하여 '앱 역할'을 할당받으세요."
                )
            
            raise NotFoundException("TENANT_NOT_REGISTERED|등록된 조직 정보가 없습니다. 조직 관리자 계정으로 로그인이 필요합니다.")

        return GetTenantStatusResponse(
            tenant_id=tenantEntity.tenant_id,
            registered_at=tenantEntity.registered_at,
            privileged_accounts=tenantEntity.privileged_accounts,
        )
