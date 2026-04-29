import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domains.agent.usecases.discover_agent_resources_use_case import DiscoverAgentResourcesUseCase
from app.domains.agent.models import AgentStatus

@pytest.mark.asyncio
async def test_discover_agent_resources_success():
    # Arrange
    mock_arm_service = MagicMock()
    mock_arm_service.list_resources_by_tag = AsyncMock(return_value=[
        {
            "name": "stlogdr_new",
            "id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/stlogdr_new",
            "location": "koreacentral",
            "createdTime": "2024-04-29T12:00:00Z"
        },
        {
            "name": "stlogdr_old",
            "id": "/subscriptions/sub1/resourceGroups/rg1/providers/Microsoft.Storage/storageAccounts/stlogdr_old",
            "location": "koreacentral",
            "createdTime": "2024-04-29T11:00:00Z"
        }
    ])
    
    mock_agent_repo = MagicMock()
    # 이미 활성화된 에이전트 없음
    mock_agent_repo.get_agent_by_subscription = AsyncMock(return_value=None)
    mock_agent_repo.get_all_by_tenant_id = AsyncMock(return_value=[])
    
    use_case = DiscoverAgentResourcesUseCase(mock_arm_service, mock_agent_repo)
    
    # Act
    results = await use_case.execute(
        sso_token="token",
        subscription_id="sub1",
        tenant_id="tenant1"
    )
    
    # Assert
    assert len(results) == 2
    # 최신 것이 첫 번째로 와야 함
    assert results[0].storage_account_name == "stlogdr_new"
    assert results[1].storage_account_name == "stlogdr_old"
    assert results[0].is_registered is False
