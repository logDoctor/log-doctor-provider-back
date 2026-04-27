import httpx
import structlog

from app.core.auth.services.auth_provider import TokenProvider
from app.core.config import settings

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

    async def send_direct_card_to_user(
        self,
        aad_object_id: str,
        customer_tenant_id: str,
        card_content: dict,
        service_url: str | None = None,
    ) -> bool:
        """Bot Framework Connector API로 1:1 대화를 생성하고 Adaptive Card를 전송합니다."""
        base_url = (service_url or self.default_service_url).rstrip("/")
        token = await self.token_provider.get_bot_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        bot_id = f"28:{settings.CLIENT_ID}"
        create_payload = {
            "bot": {"id": bot_id},
            "members": [
                {
                    "id": aad_object_id,
                    "aadObjectId": aad_object_id,
                }
            ],
            "channelData": {"tenant": {"id": customer_tenant_id}},
            "isGroup": False,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                f"{base_url}/v3/conversations",
                json=create_payload,
                headers=headers,
            )
            if res.status_code not in (200, 201):
                logger.error(
                    "create_direct_conversation_failed",
                    aad_object_id=aad_object_id,
                    status=res.status_code,
                    body=res.text,
                )
                return False
            conversation_id = res.json().get("id")

        return await self.send_adaptive_card(
            channel_id=conversation_id, 
            card_content=card_content, 
            service_url=service_url,
            tenant_id=customer_tenant_id
        )

    async def send_adaptive_card(
        self, 
        channel_id: str, 
        card_content: dict, 
        service_url: str | None = None,
        tenant_id: str | None = None
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

        # 🚀 멀티테넌트 봇의 경우 채널 전송 시 tenantId가 누락되면 실패할 수 있습니다.
        if tenant_id:
            payload["channelData"] = {"tenant": {"id": tenant_id}}

        async with httpx.AsyncClient(headers=headers) as client:
            try:
                res = await client.post(url, json=payload)
                if res.status_code in [200, 201, 202]:
                    logger.info(
                        "Teams adaptive card sent successfully",
                        channel_id=channel_id,
                        status=res.status_code,
                    )
                    return True

                logger.error(
                    "Failed to send teams adaptive card",
                    channel_id=channel_id,
                    code=res.status_code,
                    text=res.text,
                    tenant_id=tenant_id
                )
                return False
            except Exception as e:
                logger.error("Teams adaptive card service error", error=str(e), channel_id=channel_id)
                return False

