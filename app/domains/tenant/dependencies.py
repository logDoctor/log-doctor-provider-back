from fastapi import Depends

from app.infra.db.cosmos import CosmosDB

from .repository import AzureTenantRepository, TenantRepository
from .usecases import GetTenantStatusUseCase, RegisterTenantUseCase


async def get_tenant_repository() -> TenantRepository:
    """Returns the concrete implementation of TenantRepository with pre-initialized container."""
    container = await CosmosDB.get_container("tenants")
    return AzureTenantRepository(container)


def get_tenant_status_use_case(
    repository: TenantRepository = Depends(get_tenant_repository),
) -> GetTenantStatusUseCase:
    """Returns a GetTenantStatusUseCase instance with the injected repository."""
    return GetTenantStatusUseCase(repository)


def get_register_tenant_use_case(
    repository: TenantRepository = Depends(get_tenant_repository),
) -> RegisterTenantUseCase:
    """Returns a RegisterTenantUseCase instance with the injected repository."""
    return RegisterTenantUseCase(repository)
