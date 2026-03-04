from fastapi import Depends
from app.domains.tenant.dependencies import get_tenant_repository
from app.domains.tenant.repository import TenantRepository

from .repository import AzureSubscriptionRepository, SubscriptionRepository
from .usecases import GetSubscriptionSetupInfoUseCase, GetSubscriptionsUseCase
from app.domains.package.usecases import GetPackageUseCase
from app.domains.package.dependencies import get_package_use_case


def get_subscription_repository() -> SubscriptionRepository:
    return AzureSubscriptionRepository()


def get_subscriptions_use_case(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> GetSubscriptionsUseCase:
    return GetSubscriptionsUseCase(repository, tenant_repository)


def get_subscription_setup_info_use_case(
    package_use_case: GetPackageUseCase = Depends(get_package_use_case),
) -> GetSubscriptionSetupInfoUseCase:
    return GetSubscriptionSetupInfoUseCase(package_use_case)
