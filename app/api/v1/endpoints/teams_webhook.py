import structlog
from fastapi import Depends, Request

from app.core.routing import APIRouter
from app.domains.agent.dependencies import get_tenant_admin_uninstall_use_case
from app.domains.agent.usecases import TenantAdminUninstallUseCase

logger = structlog.get_logger()

router = APIRouter(tags=["Teams Webhook"])


@router.post("")
async def receive_webhook(
    request: Request,
    uninstall_use_case: TenantAdminUninstallUseCase = Depends(
        get_tenant_admin_uninstall_use_case
    ),
):
    """
    Teams Bot Framework에서 보내는 Webhook 이벤트를 수신합니다.
    """
    payload = await request.json()
    activity_type = payload.get("type")

    # 1. installationUpdate 이벤트 확인 (앱 설치/업데이트/제거)
    if activity_type == "installationUpdate":
        action = payload.get("action")
        tenant_id = payload.get("conversation", {}).get("tenantId")
        user_id = payload.get("from", {}).get("aadObjectId")

        if action == "remove":
            logger.info(
                "Teams App Uninstall Detected via Webhook",
                tenant_id=tenant_id,
                user_id=user_id,
            )
            if tenant_id and user_id:
                # 비동기로 리소스 삭제 트리거 (응답 속도를 위해)
                # 실제 운영 환경에서는 BackgroundTasks를 사용하는 것이 좋습니다.
                await uninstall_use_case.execute(tenant_id, user_id)

    # Teams Bot Framework는 일반적으로 200 OK 또는 202 Accepted를 기대합니다.
    return {"status": "received"}
