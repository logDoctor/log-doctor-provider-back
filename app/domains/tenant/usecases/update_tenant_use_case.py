import structlog

from app.core.auth.models import Identity
from app.core.auth.services.graph_service import GraphService
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.domains.tenant.repository import TenantRepository
from app.domains.tenant.schemas import GetTenantStatusResponse, UpdateTenantRequest

logger = structlog.get_logger()


class UpdateTenantUseCase:
    """
    PATCH /tenants/me 엔드포인트에서 테넌트의 부분 업데이트를 수행합니다.
    현재는 privileged_accounts(운영자 계정 리스트) 업데이트만 지원합니다.
    """

    def __init__(self, repository: TenantRepository, graph_service: GraphService):
        self.repository = repository
        self.graph_service = graph_service

    async def execute(self, identity: Identity, payload: UpdateTenantRequest) -> GetTenantStatusResponse:
        tid = identity.tenant_id

        tenant_entity = await self.repository.get_by_id(tid)
        if not tenant_entity:
            raise NotFoundException("TENANT_NOT_REGISTERED|등록된 테넌트 정보가 없습니다.")

        if payload.privileged_accounts:
            current_user_email = identity.email
            privileged_accounts = tenant_entity.privileged_accounts
            
            if not identity.is_global_admin and current_user_email not in privileged_accounts:
                raise UnauthorizedException("ACCESS_DENIED|NOT_ASSIGNED|테넌트 설정값을 변경할 권한이 없거나, 등록된 운영자가 아닙니다.")

            tenant_entity.update_privileged_accounts(
                new_accounts=payload.privileged_accounts, 
                requester_email=current_user_email
            )
            
            await self.graph_service.assign_users_to_app(tid, tenant_entity.privileged_accounts)

            saved_tenant_entity = await self.repository.upsert(tenant_entity)
        else:
            saved_tenant_entity = tenant_entity

        return GetTenantStatusResponse(
            tenant_id=saved_tenant_entity.tenant_id,
            registered_at=saved_tenant_entity.registered_at,
            privileged_accounts=saved_tenant_entity.privileged_accounts
        )

    # _prepare_privileged_accounts 메서드를 삭제됨 (도메인 엔티티로 역할 위임)
