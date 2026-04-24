from fastapi import Depends, Request
from fastapi_restful.cbv import cbv

from app.core.auth.guards import get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import (
    get_list_channels_use_case,
    get_list_joined_teams_use_case,
    get_list_resource_groups_use_case,
    get_list_subscription_administrators_use_case,
    get_register_tenant_use_case,
    get_subscription_setup_info_use_case,
    get_subscriptions_use_case,
    get_tenant_status_use_case,
    get_update_tenant_use_case,
)
from .schemas import (
    AzureResourceGroupResponse,
    GetTenantStatusResponse,
    RegisterTenantRequest,
    RegisterTenantResponse,
    SubscriptionListResponse,
    SubscriptionSetupResponse,
    UpdateTenantRequest,
    UpdateTenantResponse,
)
from .usecases import (
    GetSubscriptionSetupInfoUseCase,
    GetSubscriptionsUseCase,
    GetTenantStatusUseCase,
    ListChannelsUseCase,
    ListJoinedTeamsUseCase,
    ListResourceGroupsUseCase,
    RegisterTenantUseCase,
    UpdateTenantUseCase,
)
from .usecases.list_subscription_administrators_use_case import (
    ListSubscriptionAdministratorsUseCase,
)

router = APIRouter(tags=["Tenant"])


@cbv(router)
class TenantRouter:
    @router.get("/me", response_model=GetTenantStatusResponse)
    async def get_my_tenant_status(
        self,
        identity: Identity = Depends(get_current_identity),
        use_case: GetTenantStatusUseCase = Depends(get_tenant_status_use_case),
    ):
        """
        사용자 자신의 테넌트 등록 상태 및 에이전트 활성화 여부를 조회합니다.
        """
        return await use_case.execute(identity)

    @router.patch("/me", response_model=UpdateTenantResponse)
    async def update_my_tenant(
        self,
        request: UpdateTenantRequest,
        identity: Identity = Depends(get_current_identity),
        update_tenant_use_case: UpdateTenantUseCase = Depends(
            get_update_tenant_use_case
        ),
    ):
        """
        생성된 테넌트의 정보(운영자 계정 리스트, 알림 채널 등)를 부분 업데이트합니다.
        """
        return await update_tenant_use_case.execute(identity, request)

    @router.post("/", response_model=RegisterTenantResponse, status_code=201)
    async def register_tenant(
        self,
        request: RegisterTenantRequest,
        identity: Identity = Depends(get_current_identity),
        register_tenant_use_case: RegisterTenantUseCase = Depends(
            get_register_tenant_use_case
        ),
    ):
        """
        SSO 헤더 정보를 바탕으로 명시적으로 테넌트를 생성(가입)합니다.
        """
        return await register_tenant_use_case.execute(
            identity,
            request.privileged_accounts,
            teams_info=request.teams_info,
        )

    @router.get("/me/channels", response_model=list[dict])
    async def list_available_channels(
        self,
        team_id: str,
        identity: Identity = Depends(get_current_identity),
        use_case: ListChannelsUseCase = Depends(get_list_channels_use_case),
    ):
        """
        현재 팀 내의 알림 수신 가능한 채널 목록을 조회합니다.
        """
        return await use_case.execute(identity.tenant_id, team_id, sso_token=identity.sso_token)

    @router.get("/me/teams", response_model=list[dict])
    async def list_available_teams(
        self,
        identity: Identity = Depends(get_current_identity),
        use_case: ListJoinedTeamsUseCase = Depends(get_list_joined_teams_use_case),
    ):
        """
        사용자가 가입한 팀 목록을 조회합니다.
        """
        return await use_case.execute(identity.tenant_id, sso_token=identity.sso_token)

    # --- Subscription 관련 엔드포인트 통합 ---

    @router.get("/me/subscriptions", response_model=SubscriptionListResponse)
    async def list_user_subscriptions(
        self,
        identity: Identity = Depends(get_current_identity),
        use_case: GetSubscriptionsUseCase = Depends(get_subscriptions_use_case),
    ):
        """
        사용자가 접근 가능한 Azure 구독 목록을 조회합니다.
        """
        return await use_case.execute(identity)

    @router.get(
        "/me/subscriptions/{subscription_id}/setup-info",
        response_model=SubscriptionSetupResponse,
    )
    async def get_subscription_setup_info(
        self,
        subscription_id: str,
        request: Request,
        identity: Identity = Depends(get_current_identity),
        use_case: GetSubscriptionSetupInfoUseCase = Depends(
            get_subscription_setup_info_use_case
        ),
    ):
        """
        특정 구독에 에이전트를 설치하기 위한 설정 정보 및 Portal 링크를 조회합니다.
        """
        scheme = request.headers.get("x-forwarded-proto", "http")
        if request.headers.get("x-forwarded-port") == "443":
            scheme = "https"

        base_url = f"{scheme}://{request.url.netloc}"
        return await use_case.execute(subscription_id, base_url, identity)

    @router.get(
        "/me/subscriptions/{subscription_id}/resource-groups",
        response_model=list[AzureResourceGroupResponse],
    )
    async def list_resource_groups(
        self,
        subscription_id: str,
        identity: Identity = Depends(get_current_identity),
        use_case: ListResourceGroupsUseCase = Depends(
            get_list_resource_groups_use_case
        ),
    ):
        """
        사용자가 접근 가능한 특정 Azure 구독의 리소스 그룹 목록을 조회합니다.
        """
        return await use_case.execute(identity, subscription_id)

    @router.get(
        "/me/subscriptions/{subscription_id}/administrators",
        response_model=list[dict],
    )
    async def list_subscription_administrators(
        self,
        subscription_id: str,
        identity: Identity = Depends(get_current_identity),
        use_case: ListSubscriptionAdministratorsUseCase = Depends(
            get_list_subscription_administrators_use_case
        ),
    ):
        """
        사용자가 고른 Azure 구독의 권한자(Owner/Contributor) 중
        앱의 지정 위임자(privileged_accounts)와 교집합인 인원만 리스트업합니다.
        """
        return await use_case.execute(identity, subscription_id)
