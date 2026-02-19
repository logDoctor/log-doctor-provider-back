from fastapi import Depends

# 아까 우리가 repository.py에 작성했던 클래스들을 가져옵니다.
from .repository import AgentRepository, MockAgentRepository, CosmosAgentRepository
from .usecases.handshake_agent_use_case import HandshakeAgentUseCase

def get_agent_repository() -> AgentRepository:
    """
    어떤 DB 부품을 쓸지 결정하는 곳입니다.
    """
    # 💡 지금은 로컬에서 API가 잘 뚫렸는지 테스트해야 하므로 MockDB를 리턴합니다!
    # 나중에 실제 클라우드 환경에서는 CosmosAgentRepository()로 한 줄만 바꾸면 됩니다.
    return MockAgentRepository()

def get_handshake_agent_use_case(
    # 여기서 FastAPI의 Depends가 get_agent_repository를 실행해서 리턴값을 넣어줍니다!
    repository: AgentRepository = Depends(get_agent_repository),
) -> HandshakeAgentUseCase:
    """
    조립된 DB 부품을 Usecase(뇌)에 꽂아서 라우터로 전달합니다.
    """
    return HandshakeAgentUseCase(repository)