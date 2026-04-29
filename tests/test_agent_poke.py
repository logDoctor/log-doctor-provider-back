import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domains.agent.usecases.poke_agent_use_case import PokeAgentUseCase

@pytest.mark.asyncio
async def test_poke_agent_success():
    # Arrange
    mock_queue_service = MagicMock()
    mock_queue_service.push = AsyncMock()
    
    use_case = PokeAgentUseCase(mock_queue_service)
    
    # Act
    success = await use_case.execute(
        storage_account_name="stlogdr123",
        subscription_id="sub1"
    )
    
    # Assert
    assert success is True
    mock_queue_service.push.assert_called_once_with(
        storage_account_name="stlogdr123",
        queue_name="diagnosis-requests",
        subscription_id="sub1",
        message={"command": "WAKE_UP"}
    )
