from fastapi import Depends

from .repository import AgentRepository, AzureAgentRepository
from .usecases.handshake_agent_use_case import HandshakeAgentUseCase


def get_agent_repository() -> AgentRepository:
    return AzureAgentRepository()


def get_handshake_agent_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
) -> HandshakeAgentUseCase:
    return HandshakeAgentUseCase(repository)
