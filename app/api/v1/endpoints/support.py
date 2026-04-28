from fastapi import Body, Depends
from pydantic import BaseModel

from app.core.auth.guards import get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter
from app.domains.support.dependencies import get_support_service
from app.domains.support.service import SupportService

router = APIRouter(tags=["Support"])


class FeedbackRequest(BaseModel):
    content: str
    page_url: str | None = None


@router.post("/feedback")
async def create_feedback(
    feedback_req: FeedbackRequest = Body(...),
    identity: Identity = Depends(get_current_identity),
    support_service: SupportService = Depends(get_support_service),
):
    """
    사용자의 피드백을 수집하여 운영팀 Teams 채널로 전송합니다.
    """
    success = await support_service.send_feedback_to_teams(
        content=feedback_req.content,
        user_name=identity.name or "Unknown",
        user_email=identity.email or "Unknown",
        tenant_id=identity.tenant_id or "Unknown",
        page_url=feedback_req.page_url,
    )

    return {"status": "success" if success else "failed"}
