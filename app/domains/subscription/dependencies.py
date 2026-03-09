from fastapi import Depends

from app.domains.package.dependencies import get_agent_package_repository
from app.domains.package.repository import AgentPackageRepository
from app.domains.tenant.dependencies import get_tenant_repository
from app.domains.tenant.repository import TenantRepository
from app.infra.external.azure.azure_resource_service import AzureResourceService
from app.infra.external.azure.dependencies import get_azure_resource_service

from .repository import AzureSubscriptionRepository, SubscriptionRepository
from .usecases import GetSubscriptionSetupInfoUseCase, GetSubscriptionsUseCase


def get_subscription_repository() -> SubscriptionRepository:
    return AzureSubscriptionRepository()


def get_subscriptions_use_case(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> GetSubscriptionsUseCase:
    return GetSubscriptionsUseCase(repository, tenant_repository)


def get_subscription_setup_info_use_case(
    repository: AgentPackageRepository = Depends(get_agent_package_repository),
    azure_service: AzureResourceService = Depends(get_azure_resource_service),
) -> GetSubscriptionSetupInfoUseCase:
    return GetSubscriptionSetupInfoUseCase(repository, azure_service)
