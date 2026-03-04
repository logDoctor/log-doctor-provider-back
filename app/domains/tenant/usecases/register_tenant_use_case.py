import structlog

from app.core.auth.models import Identity
from app.core.auth.services.graph_service import GraphService
from app.domains.tenant.models import Tenant
from app.domains.tenant.repository import TenantRepository
from app.domains.tenant.schemas import RegisterTenantResponse

logger = structlog.get_logger()


class RegisterTenantUseCase:
    """
    프론트엔드에서 SSO 인증 성공 후 테넌트 등록을 명시적으로 요청(POST /tenants)할 때 사용됩니다.
    토큰에서 추출한 Tenant ID(tid)를 DB에 upsert합니다.
    """

    def __init__(self, repository: TenantRepository, graph_service: GraphService):
        self.repository = repository
        self.graph_service = graph_service

    async def execute(self, identity: Identity, privileged_accounts: list[str] = None) -> RegisterTenantResponse:
        tid = identity.tenant_id

        tenant_entity = await self.repository.get_by_id(tid)

        # 멱등성 처리: 이미 registered_at이 있다는 것은 가입 프로세스가 이미 완료되었음을 의미
        if tenant_entity and tenant_entity.is_registered():
            logger.info("Tenant already registered, returning existing status", tid=tid)
            return RegisterTenantResponse(
                tenant_id=tenant_entity.tenant_id,
                registered_at=tenant_entity.registered_at,
                privileged_accounts=tenant_entity.privileged_accounts
            )

        prepared_privileged_accounts = self._prepare_privileged_accounts(identity.email, privileged_accounts)

        # 관리자가 처음 등록할 때 자신 및 추가 운영자들을 앱에 할당 (Graph API)
        await self.graph_service.assign_users_to_app(tid, prepared_privileged_accounts)

        tenant_entity = Tenant.register(tid)

        for account in prepared_privileged_accounts:
            tenant_entity.add_privileged_account(account)
        
        saved_tenant_entity = await self.repository.upsert(tenant_entity)

        return RegisterTenantResponse(
            tenant_id=saved_tenant_entity.tenant_id,
            registered_at=saved_tenant_entity.registered_at,
            privileged_accounts=saved_tenant_entity.privileged_accounts
        )

    def _prepare_privileged_accounts(self, email: str, additional_accounts: list[str]) -> list[str]:
        """본인 이메일을 포함하고 중복을 제거한 운영자 목록을 반환합니다."""
        accounts = set(additional_accounts)
        accounts.add(email)
        return list(accounts)
