import asyncio

import structlog

from app.core.auth.services.graph_service import GraphService
from app.domains.agent.repository import AgentRepository
from app.domains.tenant.repositories import TenantRepository
from app.infra.external.teams import TeamsBotService

from .models import Notification, NotificationStatus, NotificationType
from .repository import NotificationRepository

logger = structlog.get_logger()


class NotificationService:
    """
    알림 도메인 서비스: "언제, 누구에게, 무엇을" 보낼지에 대한 비즈니스 정책을 담당합니다.
    (Option 2: 전송 성공 시에만 이력을 저장하는 Lightweight 전략)
    """

    def __init__(
        self,
        tenant_repository: TenantRepository,
        agent_repository: AgentRepository,
        teams_bot_service: TeamsBotService,
        graph_service: GraphService,
        notification_repository: NotificationRepository,
    ):
        self.tenant_repository = tenant_repository
        self.agent_repository = agent_repository
        self.teams_bot_service = teams_bot_service
        self.graph_service = graph_service
        self.notification_repository = notification_repository

    async def notify_analysis_completed(
        self, tenant_id: str, report_id: str, summary: str, agent_id: str | None = None
    ):
        """분석이 완료되었음을 채널 게시 및 활동 피드를 통해 알립니다."""
        tenant = await self.tenant_repository.get_by_id(tenant_id)
        if not tenant:
            logger.error("Tenant not found for notification", tenant_id=tenant_id)
            return

        # 🚀 에이전트 전용 채널 오버라이드 및 Fallback 로직
        teams_info = None
        if agent_id:
            agent = await self.agent_repository.get_by_id(tenant_id=tenant_id, id=agent_id)
            if agent and getattr(agent, "teams_info", None):
                teams_info = agent.teams_info

        if not teams_info and tenant.teams_info:
            teams_info = tenant.teams_info

        tasks = []
        recipient_count = 0

        # 1. 채널 알림 구성 (Teams Bot 사용 - Adaptive Card)
        if teams_info and getattr(teams_info, "channel_id", None) or (isinstance(teams_info, dict) and teams_info.get("channel_id")):
            channel_id = teams_info.channel_id if hasattr(teams_info, "channel_id") else teams_info.get("channel_id")
            service_url = teams_info.service_url if hasattr(teams_info, "service_url") else teams_info.get("service_url", "https://smba.trafficmanager.net/kr/")

            adaptive_card_payload = {
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "📊 **진단 분석 완료 (Log Doctor)**",
                        "weight": "Bolder",
                        "size": "Large",
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {"title": "진단 보고서 ID", "value": report_id},
                            {"title": "요약", "value": summary},
                        ],
                    },
                ],
                "actions": [
                    {
                        "type": "Action.OpenUrl",
                        "title": "보고서 상세보기",
                        "url": f"https://teams.microsoft.com/l/entity/ad66dd18-ef73-4fca-86d6-422f9d1759e1/index0?subEntityId={report_id}",
                    }
                ],
            }
            tasks.append(
                self.teams_bot_service.send_adaptive_card(
                    channel_id,
                    adaptive_card_payload,
                    service_url=service_url,
                )
            )
            recipient_count += 1

        # 2. 활동 피드 알림 구성
        topic = {
            "source": "text",
            "value": "진단 분석 완료 (Log Doctor)",
            "webUrl": f"https://teams.microsoft.com/l/entity/ad66dd18-ef73-4fca-86d6-422f9d1759e1/index0?subEntityId={report_id}",
        }
        for admin in tenant.privileged_accounts:
            user_id = admin.get("user_id")
            if user_id:
                tasks.append(
                    self.graph_service.send_activity_notification(
                        tenant_id, user_id, topic, f"Analysis Complete: {summary}"
                    )
                )
                recipient_count += 1

        if not tasks:
            return

        # 3. 실제 전송 수행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success_count = len([r for r in results if r is True])

        # 4. 이력 저장 (Option 2: 성공 시에만 저장)
        if success_count > 0:
            try:
                notification_record = Notification.create(
                    tenant_id=tenant_id,
                    type=NotificationType.ANALYSIS_COMPLETED,
                    summary=summary,
                    recipient_count=success_count,
                    status=NotificationStatus.SENT,
                )
                await self.notification_repository.save(notification_record)
                logger.info(
                    "Notification record saved",
                    tenant_id=tenant_id,
                    id=notification_record.notification_id,
                )
            except Exception as e:
                logger.error("Failed to save notification record", error=str(e))

        logger.info(
            "Notifications processed",
            tenant_id=tenant_id,
            report_id=report_id,
            total=len(tasks),
            success=success_count,
        )
