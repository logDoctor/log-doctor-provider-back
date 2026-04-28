from app.core.auth.dependencies import get_token_provider
from .bot_service import TeamsBotService

def get_teams_bot_service() -> TeamsBotService:
    return TeamsBotService(token_provider=get_token_provider())
