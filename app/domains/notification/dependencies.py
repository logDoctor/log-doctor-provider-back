from fastapi import Depends

from app.core.auth.dependencies import get_graph_service, get_token_provider
from app.core.auth.services.auth_provider import TokenProvider
from app.core.auth.services.graph_service import GraphService
from app.domains.agent.repositories import AgentRepository, get_agent_repository
from app.domains.tenant.dependencies import get_tenant_repository
from app.domains.tenant.repositories import TenantRepository
from app.infra.db.cosmos import CosmosDB
from app.infra.external.teams import TeamsBotService

from .repository import AzureNotificationRepository, NotificationRepository
from .service import NotificationService


async def get_notification_repository() -> NotificationRepository:
    container = await CosmosDB.get_container("notifications")
    return AzureNotificationRepository(container)


async def get_teams_bot_service(
    token_provider: TokenProvider = Depends(get_token_provider),
) -> TeamsBotService:
    """Teams Bot 서비스를 반환하는 의존성 팩토리 함수입니다."""
    return TeamsBotService(token_provider)


async def get_notification_service(
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
    agent_repository: AgentRepository = Depends(get_agent_repository),
    teams_bot_service: TeamsBotService = Depends(get_teams_bot_service),
    graph_service: GraphService = Depends(get_graph_service),
    notification_repository: NotificationRepository = Depends(
        get_notification_repository
    ),
) -> NotificationService:
    """알림 도메인 서비스를 반환하는 의존성 팩토리 함수입니다."""
    return NotificationService(
        tenant_repository,
        agent_repository,
        teams_bot_service,
        graph_service,
        notification_repository,
    )
