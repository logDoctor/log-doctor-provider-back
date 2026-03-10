import structlog

from app.core.auth.models import Identity
from app.core.auth.services.graph_service import GraphService
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.domains.tenant.repository import TenantRepository
from app.domains.tenant.schemas import UpdateTenantRequest, UpdateTenantResponse

logger = structlog.get_logger()


class UpdateTenantUseCase:
    """
    PATCH /tenants/me 엔드포인트에서 테넌트의 부분 업데이트를 수행합니다.
    현재는 privileged_accounts(운영자 계정 리스트) 업데이트만 지원합니다.
    """

    def __init__(self, repository: TenantRepository, graph_service: GraphService):
        self.repository = repository
        self.graph_service = graph_service

    async def execute(
        self, identity: Identity, payload: UpdateTenantRequest
    ) -> UpdateTenantResponse:
        tid = identity.tenant_id

        if not identity.is_admin():
            raise UnauthorizedException(
                "ACCESS_DENIED|NOT_ASSIGNED|You do not have permission to modify tenant settings."
            )

        tenant_entity = await self.repository.get_by_id(tid)
        if not tenant_entity:
            raise NotFoundException(
                "TENANT_NOT_REGISTERED|Tenant information not found."
            )

        if payload.privileged_accounts is not None:
            account_map = {
                a["email"]: a["user_id"] for a in tenant_entity.privileged_accounts
            }

            for p in payload.privileged_accounts:
                if p.user_id:
                    account_map[p.email] = p.user_id
                elif p.email not in account_map:
                    account_map[p.email] = None

            account_map[identity.email] = identity.id

            emails_to_resolve = [email for email, uid in account_map.items() if not uid]

            if emails_to_resolve:
                resolved_accounts = await self.graph_service.resolve_user_ids(
                    tid, emails_to_resolve
                )
                for ra in resolved_accounts:
                    account_map[ra["email"]] = ra["user_id"]

            for email, user_id in account_map.items():
                tenant_entity.add_privileged_account(email, user_id)

            ids_to_assign = [uid for uid in account_map.values() if uid]
            await self.graph_service.assign_users_to_app(tid, ids_to_assign)

            saved_tenant_entity = await self.repository.upsert(tenant_entity)
        else:
            saved_tenant_entity = tenant_entity

        return UpdateTenantResponse(
            tenant_id=saved_tenant_entity.tenant_id,
            registered_at=saved_tenant_entity.registered_at,
            privileged_accounts=saved_tenant_entity.privileged_accounts,
        )
