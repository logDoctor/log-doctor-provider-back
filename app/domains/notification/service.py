import asyncio
import json
import urllib.parse

import structlog

from app.core.auth.services.graph_service import GraphService
from app.core.config import settings
from app.domains.agent.repository import AgentRepository
from app.domains.tenant.repositories import TenantRepository
from app.infra.external.teams import TeamsBotService

from .models import Notification, NotificationStatus, NotificationType
from .repository import NotificationRepository

logger = structlog.get_logger()

TRANSLATIONS = {
    "ko": {
        "analysis_completed_title": "📊 **진단 분석 완료 (Log Doctor)**",
        "report_id_label": "진단 보고서 ID",
        "summary_label": "요약",
        "view_details_btn": "보고서 상세보기",
        "activity_topic": "진단 분석 완료 (Log Doctor)",
        "activity_summary_prefix": "진단 분석 완료: ",
        "detailed_diagnosis_results_available": "상세 진단 결과가 준비되었습니다.",
    },
    "en": {
        "analysis_completed_title": "📊 **Analysis Complete (Log Doctor)**",
        "report_id_label": "Report ID",
        "summary_label": "Summary",
        "view_details_btn": "View Report Details",
        "activity_topic": "Analysis Complete (Log Doctor)",
        "activity_summary_prefix": "Analysis Complete: ",
        "detailed_diagnosis_results_available": "Detailed diagnosis results available.",
    },
}


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
        self,
        tenant_id: str,
        report_id: str,
        summary: str,
        agent_id: str | None = None,
        language: str = "ko",
    ):
        """분석이 완료되었음을 채널 게시 및 활동 피드를 통해 알립니다."""
        tenant = await self.tenant_repository.get_by_id(tenant_id)
        if not tenant:
            logger.error("Tenant not found for notification", tenant_id=tenant_id)
            return

        # 🚀 에이전트 전용 채널 오버라이드 및 Fallback 로직
        teams_info = None
        if agent_id:
            agent = await self.agent_repository.get_by_id(
                tenant_id=tenant_id, id=agent_id
            )
            if agent and getattr(agent, "teams_info", None):
                teams_info = agent.teams_info

        if not teams_info and tenant.teams_info:
            teams_info = tenant.teams_info

        tasks = []
        recipient_count = 0

        # 1. 채널 알림 구성 (Teams Bot 사용 - Adaptive Card)
        if (
            teams_info
            and getattr(teams_info, "channel_id", None)
            or (isinstance(teams_info, dict) and teams_info.get("channel_id"))
        ):
            channel_id = (
                teams_info.channel_id
                if hasattr(teams_info, "channel_id")
                else teams_info.get("channel_id")
            )
            service_url = (
                teams_info.service_url
                if hasattr(teams_info, "service_url")
                else teams_info.get(
                    "service_url", "https://smba.trafficmanager.net/kr/"
                )
            )

            context_json = json.dumps({"subEntityId": report_id})
            encoded_context = urllib.parse.quote(context_json)
            deep_link = f"https://teams.microsoft.com/l/entity/{settings.TEAMS_APP_ID}/index?subEntityId={report_id}&context={encoded_context}"

            # 🚀 [FIX] en-US, ko-KR 등 다양한 언어 형식을 'en', 'ko'로 정규화하여 처리합니다.
            lang_code = (language or "ko").split("-")[0].lower()
            t = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])
            translated_summary = t.get(summary, summary)

            adaptive_card_payload = {
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": t["analysis_completed_title"],
                        "weight": "Bolder",
                        "size": "Large",
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {"title": t["report_id_label"], "value": report_id},
                            {"title": t["summary_label"], "value": translated_summary},
                        ],
                    },
                ],
                "actions": [
                    {
                        "type": "Action.OpenUrl",
                        "title": t["view_details_btn"],
                        "url": deep_link,
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
            "value": t["activity_topic"],
            "webUrl": deep_link,
        }
        for admin in tenant.privileged_accounts:
            user_id = admin.get("user_id")
            if user_id:
                tasks.append(
                    self.graph_service.send_activity_notification(
                        tenant_id,
                        user_id,
                        topic,
                        f"{t['activity_summary_prefix']}{translated_summary}",
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

    async def notify_delegation_completed(
        self,
        tenant_id: str,
        requester_email: str,
        target_user_ids: list[str],
    ) -> dict:
        """위임 완료 후 대상 운영자에게 1:1 Teams Adaptive Card를 직접 전송합니다."""
        tenant = await self.tenant_repository.get_by_id(tenant_id)
        service_url = (
            tenant.teams_info.service_url
            if tenant and tenant.teams_info and tenant.teams_info.service_url
            else None
        )

        if not target_user_ids and tenant:
            accounts = tenant.privileged_accounts or []
            target_user_ids = [
                a.get("user_id") if isinstance(a, dict) else getattr(a, "user_id", "")
                for a in accounts
            ]
            target_user_ids = [uid for uid in target_user_ids if uid]

        deep_link = f"https://teams.microsoft.com/l/entity/{settings.TEAMS_APP_ID}/index"
        card_content = {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "🏥 **Log Doctor 앱 사용 권한이 위임되었습니다**",
                    "weight": "Bolder",
                    "size": "Large",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": f"{requester_email}님이 Log Doctor AI 로그 분석 에이전트 배포 권한을 위임했습니다. 앱에 접속하여 배포를 진행하세요.",
                    "wrap": True,
                    "spacing": "Medium",
                },
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Log Doctor 앱 열기",
                    "url": deep_link,
                }
            ],
        }

        sent, failed = [], []
        for user_id in target_user_ids:
            ok = await self.teams_bot_service.send_direct_card_to_user(
                aad_object_id=user_id,
                customer_tenant_id=tenant_id,
                card_content=card_content,
                service_url=service_url,
            )
            (sent if ok else failed).append(user_id)

        logger.info(
            "delegation_notifications_processed",
            tenant_id=tenant_id,
            sent=len(sent),
            failed=len(failed),
        )
        return {"sent": sent, "failed": failed}
