from fastapi import Depends

from .repository import CosmosTenantRepository, TenantRepository
from .usecases.get_tenant_status_use_case import GetTenantStatusUseCase

def get_tenant_repository() -> TenantRepository:
    """Returns the concrete implementation of TenantRepository."""
    return CosmosTenantRepository()

def get_tenant_status_use_case(
    repository: TenantRepository = Depends(get_tenant_repository),
) -> GetTenantStatusUseCase:
    """Returns a GetTenantStatusUseCase instance with the injected repository."""
    return GetTenantStatusUseCase(repository)