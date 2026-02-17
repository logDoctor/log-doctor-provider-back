from fastapi import Depends

from .repository import AgentRepository, MockAgentRepository
from .services import AgentHandshaker


def get_agent_repository() -> AgentRepository:
    return MockAgentRepository()


def get_agent_handshaker(
    repository: AgentRepository = Depends(get_agent_repository),
) -> AgentHandshaker:
    return AgentHandshaker(repository)
