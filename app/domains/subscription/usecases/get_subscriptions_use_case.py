from app.core import security
from app.domains.subscription.repository import SubscriptionRepository
from app.domains.subscription.schemas import SubscriptionItem, SubscriptionListResponse


class GetSubscriptionsUseCase:
    def __init__(self, repository: SubscriptionRepository):
        self.repository = repository

    async def execute(self, sso_token: str) -> SubscriptionListResponse:
        # 1. 인증 방식에 따라 토큰 획득 (Managed Identity인 경우 직방으로 서비스 토큰 사용)
        from app.core.config import settings
        if settings.AUTH_METHOD == "managed_identity":
            arm_token = await security.get_service_access_token()
        else:
            # 기본적으로는 사용자를 대신하는 OBO 토큰 교환 시도
            arm_token = await security.get_obo_access_token(sso_token)

        # 2. Call Repository Directly
        raw_subscriptions = await self.repository.list_subscriptions(arm_token)

        # 3. Map to Domain Schema (Orchestration)
        subscriptions = [
            SubscriptionItem(
                subscription_id=sub["subscriptionId"],
                display_name=sub["displayName"],
            )
            for sub in raw_subscriptions
        ]

        return SubscriptionListResponse(subscriptions=subscriptions)
