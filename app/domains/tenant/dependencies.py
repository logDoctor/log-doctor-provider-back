from fastapi import Depends

from .repository import CosmosTenantRepository, TenantRepository
from .services import TenantStatusChecker


def get_tenant_repository() -> TenantRepository:
    """Returns the concrete implementation of TenantRepository."""
    return CosmosTenantRepository()


def get_status_checker(
    repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantStatusChecker:
    """Returns a TenantStatusChecker instance with the injected repository."""
    return TenantStatusChecker(repository)
