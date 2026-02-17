from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi_restful.cbv import cbv

from .dependencies import get_subscription_fetcher
from .schemas import SubscriptionListResponse
from .services import SubscriptionFetcher

router = APIRouter(prefix="/subscriptions", tags=["Subscription"])


@cbv(router)
class SubscriptionRouter:
    fetcher: SubscriptionFetcher = Depends(get_subscription_fetcher)

    @router.get("/", response_model=SubscriptionListResponse)
    async def list_user_subscriptions(
        self,
        authorization: str = Header(..., description="Bearer {Teams SSO Token}"),
    ):
        """
        사용자의 Azure 구독 목록을 조회합니다 (OBO Flow).
        """
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401, detail="Invalid authorization header format"
            )

        sso_token = authorization.split(" ")[1]
        return await self.fetcher.fetch(sso_token)
