from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.exceptions import NotFoundException, UnauthorizedException
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
        if not tenant or not tenant.registered_at:
            raise NotFoundException("TENANT_NOT_REGISTERED|등록된 테넌트 정보가 없습니다.")
        
        privileged_accounts_lower = [email.lower() for email in (tenant.privileged_accounts or [])]
        current_user_email = (identity.email or "").lower()

        if not identity.is_global_admin and current_user_email not in privileged_accounts_lower:
            raise UnauthorizedException(f"ACCESS_DENIED|NOT_ASSIGNED|접근 권한이 없습니다. 운영자에게 권한 부여를 요청하세요. (지정된 운영자: {', '.join(tenant.privileged_accounts)})")

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
