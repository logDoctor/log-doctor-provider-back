from fastapi import Depends

from app.core.auth.dependencies import get_graph_service, get_token_provider
from app.core.auth.services.auth_provider import TokenProvider
from app.core.auth.services.graph_service import GraphService
from app.infra.db.cosmos import CosmosDB

from .repository import AzureTenantRepository, TenantRepository
from .usecases import (
    GetTenantStatusUseCase,
    RegisterTenantUseCase,
    UpdateTenantUseCase,
)


async def get_tenant_repository() -> TenantRepository:
    """Returns the concrete implementation of TenantRepository with pre-initialized container."""
    container = await CosmosDB.get_container("tenants")
    return AzureTenantRepository(container)

def get_tenant_status_use_case(
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
    token_provider: TokenProvider = Depends(get_token_provider),
) -> GetTenantStatusUseCase:
    """Returns a GetTenantStatusUseCase instance with the injected repository and token provider."""
    return GetTenantStatusUseCase(tenant_repository, token_provider)


def get_register_tenant_use_case(
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
    graph_service: GraphService = Depends(get_graph_service),
) -> RegisterTenantUseCase:
    """Returns a RegisterTenantUseCase instance with the injected repository and graph service."""
    return RegisterTenantUseCase(tenant_repository, graph_service)


def get_update_tenant_use_case(
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
    graph_service: GraphService = Depends(get_graph_service),
) -> UpdateTenantUseCase:
    """Returns an UpdateTenantUseCase instance with injected dependencies."""
    return UpdateTenantUseCase(tenant_repository, graph_service)
