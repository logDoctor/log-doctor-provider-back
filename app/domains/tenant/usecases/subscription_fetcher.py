import logging
from app.domains.tenant.azure_repository import AzureRepository
from app.domains.tenant.schemas import GetSubscriptionsResponse, SubscriptionInfo


class SubscriptionFetcher:
    # 외부 통신을 담당할 AzureRepository 부품을 주입받습니다.
    def __init__(self, azure_repository: AzureRepository):
        self.azure_repository = azure_repository

    async def execute(self, sso_token: str) -> GetSubscriptionsResponse:
        logging.info(
            f"🔍 [OBO Flow] 프론트엔드로부터 구독 목록 조회 요청 수신 (Token: {sso_token[:10]}...)"
        )

        # 1. Repository를 시켜서 Azure에서 진짜(혹은 가짜) 구독 데이터를 가져옵니다.
        raw_subscriptions = await self.azure_repository.get_subscriptions_via_obo(
            sso_token
        )

        # 2. 프론트엔드가 쓰기 편하게 Pydantic 모델(SubscriptionInfo)로 예쁘게 포장합니다.
        formatted_subs = [
            SubscriptionInfo(
                subscription_id=sub["subscription_id"],
                display_name=sub["display_name"],
                state=sub["state"],
            )
            for sub in raw_subscriptions
        ]

        # 3. 최종 응답 반환
        return GetSubscriptionsResponse(subscriptions=formatted_subs)
