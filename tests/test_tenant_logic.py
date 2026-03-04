import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domains.tenant.usecases.register_tenant_use_case import RegisterTenantUseCase
from app.domains.tenant.usecases.get_tenant_status_use_case import GetTenantStatusUseCase
from app.core.auth.models import Identity, IdentityType
from app.domains.tenant.models import Tenant

@pytest.mark.asyncio
async def test_register_tenant_success():
    # Arrange
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)
    mock_repo.upsert = AsyncMock(side_effect=lambda x: x)
    
    use_case = RegisterTenantUseCase(repository=mock_repo)
    identity = Identity(
        type=IdentityType.CLIENT_AGENT,
        id="user-oid",
        name="Test User",
        roles=[],
        tenant_id="new-tenant-id"
    )

    # Act
    response = await use_case.execute(identity)

    # Assert
    assert response.tenant_id == "new-tenant-id"
    assert response.is_registered is True
    assert response.registered_at is not None
    mock_repo.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_get_tenant_status_registered():
    # Arrange
    now_str = "2026-02-26T00:00:00.000000+00:00"
    tenant_obj = Tenant.create("existing-tenant-id")
    tenant_obj.is_active = True
    tenant_obj.registered_at = now_str
    
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=tenant_obj)
    
    use_case = GetTenantStatusUseCase(repository=mock_repo)

    # Act
    response = await use_case.execute("existing-tenant-id")

    # Assert
    assert response.tenant_id == "existing-tenant-id"
    assert response.is_registered is True
    # Pydantic parses the string into a datetime object, so we compare with isoforest()
    assert response.registered_at.isoformat() == now_str
