from app.core.auth.dependencies import get_graph_service, get_token_provider
from app.core.auth.services.auth_provider import TokenProvider
from app.core.auth.services.graph_service import GraphService
from app.core.interfaces.azure_arm import AzureArmService
from app.domains.package.dependencies import get_agent_package_repository
from app.domains.package.repository import AgentPackageRepository
from app.infra.db.cosmos import CosmosDB
from app.infra.external.azure.dependencies import (
    get_azure_arm_client,
    get_azure_arm_service,
)
from fastapi import Depends

from .repositories import (
    AzureSubscriptionRepository,
    AzureTenantRepository,
    SubscriptionRepository,
    TenantRepository,
)
from .usecases import (
    GetSubscriptionSetupInfoUseCase,
    GetSubscriptionsUseCase,
    GetTenantStatusUseCase,
    ListChannelsUseCase,
    RegisterTenantUseCase,
    UpdateTenantUseCase,
)


async def get_tenant_repository() -> TenantRepository:
    """Returns the concrete implementation of TenantRepository with pre-initialized container."""
    container = await CosmosDB.get_container("tenants")
    return AzureTenantRepository(container)


def get_subscription_repository(
    arm_client=Depends(get_azure_arm_client),
) -> SubscriptionRepository:
    """Returns the concrete implementation of SubscriptionRepository."""
    return AzureSubscriptionRepository(arm_client)


async def get_tenant_status_use_case(
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
    token_provider: TokenProvider = Depends(get_token_provider),
) -> GetTenantStatusUseCase:
    """Returns a GetTenantStatusUseCase instance with the injected repository and token provider."""
    return GetTenantStatusUseCase(tenant_repository, token_provider)


async def get_subscriptions_use_case(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> GetSubscriptionsUseCase:
    """Returns a GetSubscriptionsUseCase instance."""
    return GetSubscriptionsUseCase(repository, tenant_repository)


def get_subscription_setup_info_use_case(
    repository: AgentPackageRepository = Depends(get_agent_package_repository),
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
) -> GetSubscriptionSetupInfoUseCase:
    """Returns a GetSubscriptionSetupInfoUseCase instance."""
    return GetSubscriptionSetupInfoUseCase(repository, azure_arm_service)


async def get_register_tenant_use_case(
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
    graph_service: GraphService = Depends(get_graph_service),
) -> RegisterTenantUseCase:
    """Returns a RegisterTenantUseCase instance with the injected repository and graph service."""
    return RegisterTenantUseCase(tenant_repository, graph_service)


async def get_update_tenant_use_case(
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
    graph_service: GraphService = Depends(get_graph_service),
) -> UpdateTenantUseCase:
    """Returns an UpdateTenantUseCase instance with injected dependencies."""
    return UpdateTenantUseCase(tenant_repository, graph_service)


def get_list_channels_use_case(
    graph_service: GraphService = Depends(get_graph_service),
) -> ListChannelsUseCase:
    """Returns a ListChannelsUseCase instance with injected dependencies."""
    return ListChannelsUseCase(graph_service)
    return ListChannelsUseCase(graph_service)
