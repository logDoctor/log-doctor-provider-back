from fastapi import Depends
from fastapi_restful.cbv import cbv
from pydantic import BaseModel

from app.core.auth.guards import get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import get_notification_service
from .service import NotificationService

router = APIRouter(tags=["Notification"])


class NotifyDelegationRequest(BaseModel):
    target_user_ids: list[str] = []


@cbv(router)
class NotificationRouter:
    @router.post("/delegation", response_model=dict)
    async def notify_delegation_completed(
        self,
        request: NotifyDelegationRequest,
        identity: Identity = Depends(get_current_identity),
        notification_service: NotificationService = Depends(get_notification_service),
    ):
        """
        위임 완료 후 대상 운영자에게 1:1 Teams Adaptive Card를 직접 전송합니다.
        """
        return await notification_service.notify_delegation_completed(
            tenant_id=identity.tenant_id,
            requester_email=identity.email,
            target_user_ids=request.target_user_ids,
        )
