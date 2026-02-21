from app.core import security
from app.domains.subscription.repository import SubscriptionRepository
from app.domains.subscription.schemas import SubscriptionItem, SubscriptionListResponse


class GetSubscriptionsUseCase:
    def __init__(self, repository: SubscriptionRepository):
        self.repository = repository

    async def execute(self, sso_token: str) -> SubscriptionListResponse:
        # 1. OBO Token Exchange (사용자 권한 대행 - 휴대폰 MFA가 필요한 경우 이 경로를 사용)
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
