from app.core.auth.constants import AppRoleName
from app.core.auth.models import Identity
from app.core.auth.services.graph_service import GraphService
from app.core.exceptions import ConflictException
from app.domains.tenant.models import TeamsInfo, Tenant
from app.domains.tenant.schemas import (
    PrivilegedAccountRequest,
    RegisterTenantResponse,
    TeamsInfoPayload,
)

from ..repositories import TenantRepository


class RegisterTenantUseCase:
    """
    프론트엔드에서 SSO 인증 성공 후 테넌트 등록을 명시적으로 요청(POST /tenants)할 때 사용됩니다.
    토큰에서 추출한 Tenant ID(tid)를 DB에 upsert합니다.
    """

    def __init__(self, repository: TenantRepository, graph_service: GraphService):
        self.repository = repository
        self.graph_service = graph_service

    async def execute(
        self,
        identity: Identity,
        privileged_accounts: list[PrivilegedAccountRequest] = None,
        teams_info: TeamsInfoPayload | None = None,
    ) -> RegisterTenantResponse:
        tid = identity.tenant_id
        sso_token = identity.sso_token

        tenant = await self.repository.get_by_id(tid)

        if tenant and tenant.is_registered():
            raise ConflictException(
                "TENANT_ALREADY_REGISTERED|This tenant is already registered."
            )

        # 🛡️ [REFINED] 현재 로그인한 사용자(본인)는 토큰의 oid(identity.id)를 직접 사용합니다.
        # 이메일 조회를 건너뛰어 404 Resolution 에러를 원천 차단합니다.
        resolved_accounts = [{"email": identity.email, "user_id": identity.id}]

        # 본인 외 추가 운영자만 Graph API로 ID를 조회합니다.
        other_emails = [
            a.email for a in privileged_accounts 
            if privileged_accounts and a.email.lower() != identity.email.lower()
        ]
        
        if other_emails:
            resolved_others = await self.graph_service.resolve_user_ids(
                tid, other_emails, sso_token=sso_token
            )
            resolved_accounts.extend(resolved_others)

        tenant = Tenant.register(tid)
        if teams_info:
            tenant.teams_info = TeamsInfo(
                team_id=teams_info.team_id,
                channel_id=teams_info.channel_id,
                service_url=teams_info.service_url,
            )

        # 중복 제거 및 계정 추가
        seen_ids = set()
        for account in resolved_accounts:
            if account["user_id"] not in seen_ids:
                tenant.add_privileged_account(account["email"], account["user_id"])
                seen_ids.add(account["user_id"])

        # 자기 자신(최초 등록자)은 TenantAdmin, 나머지는 PrivilegedUser로 분리 할당
        admin_id = identity.id

        if admin_id:
            await self.graph_service.assign_user_to_app(
                tid, admin_id, AppRoleName.TENANT_ADMIN_ID, sso_token=sso_token
            )

        other_ids = [
            a["user_id"] for a in resolved_accounts if a["user_id"] != admin_id
        ]
        if other_ids:
            await self.graph_service.assign_users_to_app(
                tid, other_ids, AppRoleName.PRIVILEGED_USER_ID, sso_token=sso_token
            )

        saved_tenant = await self.repository.upsert(tenant)

        return RegisterTenantResponse(
            tenant_id=saved_tenant.tenant_id,
            registered_at=saved_tenant.registered_at,
            privileged_accounts=saved_tenant.privileged_accounts,
            teams_info=TeamsInfoPayload(
                team_id=saved_tenant.teams_info.team_id,
                channel_id=saved_tenant.teams_info.channel_id,
                service_url=saved_tenant.teams_info.service_url,
            )
            if saved_tenant.teams_info
            else None,
        )

    def _prepare_privileged_accounts(
        self, email: str, additional_accounts: list[str]
    ) -> list[str]:
        """본인 이메일을 포함하고 중복을 제거한 운영자 목록을 반환합니다."""
        accounts = set(additional_accounts)
        accounts.add(email)
        return list(accounts)
