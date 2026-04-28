from app.infra.external.teams.dependencies import get_teams_bot_service
from fastapi import Depends

from app.infra.external.teams.bot_service import TeamsBotService

from .service import SupportService


def get_support_service(
    teams_bot_service: TeamsBotService = Depends(get_teams_bot_service),
) -> SupportService:
    return SupportService(teams_bot_service)
