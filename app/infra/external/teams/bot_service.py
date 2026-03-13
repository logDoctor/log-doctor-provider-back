import httpx
import structlog

from app.core.auth.services.auth_provider import TokenProvider

logger = structlog.get_logger()


class TeamsBotService:
    """
    Teams Bot Framework(Connector API)를 통해 메시지를 전송하는 서비스입니다.
    Graph API 권한이 아닌 봇 토큰을 사용하여 멀티테넌트 환경에서 안정적으로 작동합니다.
    """

    def __init__(self, token_provider: TokenProvider):
        self.token_provider = token_provider
        # 기본 서비스 URL (테넌트 배포 시점에 따라 바뀔 수 있음)
        self.default_service_url = "https://smba.trafficmanager.net/kr/"

    async def send_message(
        self, channel_id: str, content: str, service_url: str | None = None
    ) -> bool:
        """
        지정된 채널로 텍스트 메시지를 발송합니다.
        """
        base_url = service_url or self.default_service_url
        # Connector API 엔드포인트 조립
        url = f"{base_url.rstrip('/')}/v3/conversations/{channel_id}/activities"

        token = await self.token_provider.get_bot_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Teams Activity Payload 조립
        payload = {
            "type": "message",
            "text": content,
        }

        async with httpx.AsyncClient(headers=headers) as client:
            try:
                res = await client.post(url, json=payload)
                if res.status_code in [200, 201, 202]:
                    logger.info(
                        "Teams bot message sent successfully",
                        channel_id=channel_id,
                        status=res.status_code,
                    )
                    return True

                logger.error(
                    "Failed to send teams bot message",
                    channel_id=channel_id,
                    code=res.status_code,
                    text=res.text,
                )
                return False
            except Exception as e:
                logger.error("Teams bot service error", error=str(e))
                return False

    async def send_adaptive_card(
        self, channel_id: str, card_content: dict, service_url: str | None = None
    ) -> bool:
        """
        Adaptive Card 형태의 미려한 알림을 발송합니다.
        """
        base_url = service_url or self.default_service_url
        url = f"{base_url.rstrip('/')}/v3/conversations/{channel_id}/activities"

        token = await self.token_provider.get_bot_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": card_content,
                }
            ],
        }

        async with httpx.AsyncClient(headers=headers) as client:
            res = await client.post(url, json=payload)
            return res.status_code in [200, 201, 202]

