from fastapi import APIRouter, Depends, Request
from fastapi_restful.cbv import cbv

from app.core.auth import get_sso_token
from app.core.config import settings

from .dependencies import (
    get_subscription_setup_info_use_case,
    get_subscriptions_use_case,
)
from .schemas import SubscriptionListResponse, SubscriptionSetupResponse
from .usecases import GetSubscriptionSetupInfoUseCase, GetSubscriptionsUseCase

router = APIRouter(prefix="/subscriptions", tags=["Subscription"])


@cbv(router)
class SubscriptionRouter:
    get_subscriptions_use_case: GetSubscriptionsUseCase = Depends(
        get_subscriptions_use_case
    )
    get_subscription_setup_info_use_case: GetSubscriptionSetupInfoUseCase = Depends(
        get_subscription_setup_info_use_case
    )

    @router.get("/", response_model=SubscriptionListResponse)
    async def list_user_subscriptions(
        self,
        sso_token: str = Depends(get_sso_token),
    ):
        return await self.get_subscriptions_use_case.execute(sso_token)

    @router.get(
        "/{subscription_id}/setup-info", response_model=SubscriptionSetupResponse
    )
    async def get_subscription_setup_info(
        self,
        subscription_id: str,
        request: Request,
    ):
        # Azure Container Apps 환경 또는 운영 환경에서는 항상 HTTPS를 사용하도록 강제합니다.
        scheme = request.url.scheme
        if "azurecontainerapps.io" in request.url.netloc or not settings.DEBUG:
            scheme = "https"

        base_url = f"{scheme}://{request.url.netloc}"
        return await self.get_subscription_setup_info_use_case.execute(
            subscription_id, base_url
        )
