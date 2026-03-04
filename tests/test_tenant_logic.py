from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.auth.models import Identity, IdentityType
from app.domains.tenant.models import Tenant
from app.domains.tenant.usecases.get_tenant_status_use_case import (
    GetTenantStatusUseCase,
)
from app.domains.tenant.usecases.register_tenant_use_case import RegisterTenantUseCase


@pytest.mark.asyncio
async def test_register_tenant_success():
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)
    mock_repo.upsert = AsyncMock(side_effect=lambda x: x)
    
    mock_graph = MagicMock()
    use_case = RegisterTenantUseCase(repository=mock_repo, graph_service=mock_graph)
    identity = Identity(
        type=IdentityType.CLIENT_AGENT,
        id="user-oid",
        name="Test User",
        email="test@user.com",
        roles=[],
        tenant_id="new-tenant-id",
        sso_token="test_token"
    )

    # Act
    response = await use_case.execute(identity, additional_accounts=[])

    # Assert
    assert response.tenant_id == "new-tenant-id"
    assert response.is_registered is True
    assert response.registered_at is not None
    mock_repo.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_get_tenant_status_registered():
    # Arrange
    now_str = "2026-02-26T00:00:00.000000+00:00"
    tenant_obj = Tenant.register("existing-tenant-id")
    tenant_obj.is_active = True
    tenant_obj.registered_at = now_str
    
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=tenant_obj)
    
    mock_token = MagicMock()
    mock_token.get_obo_token = AsyncMock(return_value="mock_token")
    use_case = GetTenantStatusUseCase(tenant_repository=mock_repo, token_provider=mock_token)

    identity = Identity(
        type=IdentityType.CLIENT_AGENT,
        id="user-oid",
        name="Test User",
        email="test@user.com",
        roles=[],
        tenant_id="existing-tenant-id",
        sso_token="test_token"
    )

    # Act
    response = await use_case.execute(identity)

    # Assert
    assert response.tenant_id == "existing-tenant-id"
    assert response.is_registered is True
    # Pydantic parses the string into a datetime object, so we compare with isoforest()
    assert response.registered_at.isoformat() == now_str
