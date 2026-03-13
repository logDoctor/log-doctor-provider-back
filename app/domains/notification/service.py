import asyncio

import structlog

from app.core.auth.services.graph_service import GraphService
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
        teams_bot_service: TeamsBotService,
        graph_service: GraphService,
        notification_repository: NotificationRepository,
    ):
        self.tenant_repository = tenant_repository
        self.teams_bot_service = teams_bot_service
        self.graph_service = graph_service
        self.notification_repository = notification_repository

    async def notify_analysis_completed(
        self, tenant_id: str, report_id: str, summary: str
    ):
        """분석이 완료되었음을 채널 게시 및 활동 피드를 통해 알립니다."""
        tenant = await self.tenant_repository.get_by_id(tenant_id)
        if not tenant:
            logger.error("Tenant not found for notification", tenant_id=tenant_id)
            return

        tasks = []
        recipient_count = 0

        # 1. 채널 알림 구성 (Teams Bot 사용)
        if (
            tenant.teams_info
            and tenant.teams_info.channel_id
        ):
            message_content = (
                f"✅ **Analysis Completed**\n\n"
                f"Report ID: `{report_id}`\n"
                f"Summary: {summary}\n\n"
                f"[View Report](https://teams.microsoft.com/l/entity/{tenant_id}/index0)"
            )
            tasks.append(
                self.teams_bot_service.send_message(
                    tenant.teams_info.channel_id,
                    message_content,
                    service_url=tenant.teams_info.service_url,
                )
            )
            recipient_count += 1

        # 2. 활동 피드 알림 구성
        topic = {
            "value": f"https://teams.microsoft.com/l/entity/{tenant_id}/index0",
            "webUrl": f"https://teams.microsoft.com/l/entity/{tenant_id}/index0",
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
                    status=NotificationStatus.SENT
                )
                await self.notification_repository.save(notification_record)
                logger.info("Notification record saved", tenant_id=tenant_id, id=notification_record.notification_id)
            except Exception as e:
                logger.error("Failed to save notification record", error=str(e))

        logger.info(
            "Notifications processed",
            tenant_id=tenant_id,
            report_id=report_id,
            total=len(tasks),
            success=success_count,
        )
