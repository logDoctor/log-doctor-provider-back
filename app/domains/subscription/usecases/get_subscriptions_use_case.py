from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.exceptions import UnauthorizedException
from app.domains.subscription.repository import SubscriptionRepository
from app.domains.subscription.schemas import SubscriptionItem, SubscriptionListResponse
from app.domains.tenant.repository import TenantRepository


class GetSubscriptionsUseCase:
    def __init__(self, repository: SubscriptionRepository, tenant_repository: TenantRepository):
        self.repository = repository
        self.tenant_repository = tenant_repository

    async def execute(self, identity: Identity) -> SubscriptionListResponse:
        # 1. Authorization Check: 이 계정이 테넌트의 지정된 운영자인지 확인
        tenant = await self.tenant_repository.get_by_id(identity.tenant_id)
        
        # 🛡️ [SECURITY] 테넌트가 등록되지 않았더라도 '전역 관리자' 또는 '앱 역할(App Role) 보유자'라면 구독 조회를 허용합니다.
        # 이를 통해 지정된 담당자가 관리자 동의 후 직접 설치를 진행할 수 있습니다.
        is_registered = tenant and tenant.registered_at
        
        if not is_registered:
            has_permission = identity.is_global_admin or len(identity.roles) > 0
            if not has_permission:
                raise UnauthorizedException(
                    "ACCESS_DENIED|NOT_ASSIGNED|로그닥터 앱을 사용할 권한이 없습니다. "
                    "조직 관리자에게 '엔터프라이즈 애플리케이션'에서 앱 역할을 할당받으세요."
                )
            # 권한이 있는 경우(GA 또는 Role 보유), 미등록 상태에서도 OBO 토큰 교환 단계로 넘어갑니다.
            privileged_emails = []
        else:
            privileged_emails = [a["email"].lower() for a in (tenant.privileged_accounts or []) if "email" in a]

        current_user_email = (identity.email or "").lower()

        # 이미 등록된 테넌트인 경우에만 권한 체크 수행 (미등록 상태의 전역 관리자는 위에서 통과됨)
        if is_registered and not identity.is_global_admin and current_user_email not in privileged_emails:
            display_emails = ", ".join(privileged_emails)
            raise UnauthorizedException(f"ACCESS_DENIED|NOT_ASSIGNED|접근 권한이 없습니다. 운영자에게 권한 부여를 요청하세요. (지정된 운영자: {display_emails})")

        # 2. OBO Token Exchange
        arm_token = await get_obo_access_token(identity.sso_token)

        # 3. Call Repository Directly
        raw_subscriptions = await self.repository.list_subscriptions(arm_token)

        # 4. Map to Domain Schema (Orchestration)
        subscriptions = [
            SubscriptionItem(
                subscription_id=sub["subscriptionId"],
                display_name=sub["displayName"],
            )
            for sub in raw_subscriptions
        ]

        return SubscriptionListResponse(subscriptions=subscriptions)
