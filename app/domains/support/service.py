import structlog

from app.core.config import settings
from app.infra.external.teams.bot_service import TeamsBotService

logger = structlog.get_logger()


class SupportService:
    def __init__(self, teams_bot_service: TeamsBotService):
        self.teams_bot_service = teams_bot_service

    async def send_feedback_to_teams(
        self,
        content: str,
        user_name: str,
        user_email: str,
        tenant_id: str,
        page_url: str | None = None,
    ) -> bool:
        """
        사용자의 피드백을 수집하여 운영팀 Teams 채널로 Adaptive Card 형태로 전송합니다.
        """
        channel_id = settings.SUPPORT_CHANNEL_ID
        if not channel_id:
            logger.warning(
                "SUPPORT_CHANNEL_ID not configured, feedback will only be logged"
            )
            logger.info(
                "User Feedback (Logged)",
                content=content,
                user=user_email,
                tenant=tenant_id,
            )
            return True

        # [DEFENSIVE] 만약 채널 ID가 전체 URL 형태라면 실제 ID 부분만 추출합니다.
        # 예: https://teams.microsoft.com/l/channel/19%3A...%40thread.tacv2/...
        if channel_id.startswith("https://"):
            import re
            import urllib.parse
            match = re.search(r"/channel/([^/?]+)", channel_id)
            if match:
                channel_id = urllib.parse.unquote(match.group(1))
                logger.info("Extracted channel_id from URL", extracted_id=channel_id)

        card_content = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "🚨 **새로운 버그 제보 / 문의**",
                    "weight": "Bolder",
                    "size": "Large",
                    "color": "Attention",
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "작성자", "value": f"{user_name} ({user_email})"},
                        {"title": "테넌트 ID", "value": tenant_id},
                        {"title": "페이지", "value": page_url or "Unknown"},
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": "**상세 내용:**",
                    "weight": "Bolder",
                    "spacing": "Medium",
                },
                {"type": "TextBlock", "text": content, "wrap": True},
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "사용자에게 답장 메일 쓰기",
                    "url": f"mailto:{user_email}?subject=RE: [Log Doctor] Bug Report Inquiry",
                }
            ],
        }

        return await self.teams_bot_service.send_adaptive_card(
            channel_id=channel_id,
            card_content=card_content,
            service_url=settings.SUPPORT_SERVICE_URL,
            tenant_id=tenant_id,
        )
