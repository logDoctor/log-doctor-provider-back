from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi_restful.cbv import cbv

from .dependencies import get_subscriptions_use_case
from .schemas import SubscriptionListResponse
from .usecases.get_subscriptions_use_case import GetSubscriptionsUseCase
from app.domains.tenant.dependencies import get_current_user_and_sync

router = APIRouter(prefix="/subscriptions", tags=["Subscription"])


@cbv(router)
class SubscriptionRouter:
    use_case: GetSubscriptionsUseCase = Depends(get_subscriptions_use_case)

    @router.get("/", response_model=SubscriptionListResponse)
    async def list_user_subscriptions(
        self,
        authorization: str = Header(..., description="Bearer {Teams SSO Token}"),
        user_info: dict = Depends(get_current_user_and_sync),
    ):
        """
        사용자의 Azure 구독 목록을 조회합니다 (OBO Flow).
        * `get_current_user_and_sync`를 통과했으므로 토큰은 위조되지 않았으며, 회원(Tenant, User) 정보가 DB에 동기화된 상태입니다.
        """
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401, detail="Invalid authorization header format"
            )

        sso_token = authorization.split(" ")[1]
        try:
            return await self.use_case.execute(sso_token)
        except ValueError as e:
            if str(e).startswith("MFA_REQUIRED|"):
                claims = str(e).split("|")[1]
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "mfa_required",
                        "message": "MFA(다단계 인증)가 필요합니다. 휴대폰 인증을 진행해주세요.",
                        "claims": claims
                    }
                )
            raise HTTPException(status_code=500, detail=str(e))
