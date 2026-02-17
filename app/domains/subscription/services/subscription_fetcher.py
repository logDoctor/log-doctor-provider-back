from app.core import security
from app.domains.subscription.repository import SubscriptionRepository
from app.domains.subscription.schemas import SubscriptionItem, SubscriptionListResponse


class SubscriptionFetcher:
    def __init__(self, repository: SubscriptionRepository):
        self.repository = repository

    async def fetch(self, sso_token: str) -> SubscriptionListResponse:
        # 1. OBO Token Exchange
        arm_token = await security.get_obo_access_token(sso_token)

        # 2. Call Repository (Abstraction)
        raw_subscriptions = await self.repository.list_subscriptions(arm_token)

        # 3. Map to Domain Schema
        subscriptions = [
            SubscriptionItem(
                subscription_id=sub["subscriptionId"],  # Azure API returns camelCase
                display_name=sub["displayName"],
            )
            for sub in raw_subscriptions
        ]

        return SubscriptionListResponse(subscriptions=subscriptions)
