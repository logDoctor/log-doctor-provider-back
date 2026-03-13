from app.core.auth.models import Identity
from app.core.auth.services.auth_provider import TokenProvider
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.domains.tenant.schemas import GetTenantStatusResponse, TeamsInfoPayload

from ..repositories import TenantRepository


class GetTenantStatusUseCase:
    def __init__(
        self, tenant_repository: TenantRepository, token_provider: TokenProvider
    ):
        self.tenant_repository = tenant_repository
        self.token_provider = token_provider

    async def execute(self, identity: Identity) -> GetTenantStatusResponse:
        obo_error = None
        try:
            await self.token_provider.get_obo_token(identity.sso_token)
        except Exception as e:
            obo_error = e
            # 전역 관리자라면 우선 이 에러를 무시하고 진행합니다. (나중에 등록 가이드로 보내기 위해)
            if not identity.is_directory_admin():
                raise e

        tenant = await self.tenant_repository.get_by_id(identity.tenant_id)

        if not tenant:
            # 미등록 상태인데 전역 관리자라면 -> '가입 가이드(404)'
            if identity.is_directory_admin():
                raise NotFoundException(
                    "TENANT_NOT_REGISTERED|Tenant is not registered. Please complete the initial setup."
                )

            raise NotFoundException(
                "NOT_ASSIGNED|ACCESS_DENIED|You do not have permission to use LogDoctor."
            )

        # 3. 테넌트는 등록되어 있는데 OBO 토큰 교환에서 에러가 났던 경우
        # 이것은 '가입'은 됐으나 '권한 위임(Role Assignment)'이 안 된 전역 관리자 상황입니다.
        if obo_error and identity.is_directory_admin():
            raise UnauthorizedException(
                "ADMIN_ROLE_NOT_ASSIGNED|Global Admin account detected. "
                "Please register the tenant to assign initial roles."
            )

        return GetTenantStatusResponse(
            tenant_id=tenant.tenant_id,
            registered_at=tenant.registered_at,
            privileged_accounts=tenant.privileged_accounts,
            teams_info=TeamsInfoPayload(
                team_id=tenant.teams_info.team_id,
                channel_id=tenant.teams_info.channel_id,
                service_url=tenant.teams_info.service_url,
            )
            if tenant.teams_info
            else None,
        )
