from fastapi import Depends

from app.domains.package.dependencies import get_package_use_case
from app.domains.package.usecases import GetPackageUseCase

from .repository import AzureSubscriptionRepository, SubscriptionRepository
from .usecases import GetSubscriptionSetupInfoUseCase, GetSubscriptionsUseCase


def get_subscription_repository() -> SubscriptionRepository:
    return AzureSubscriptionRepository()


def get_subscriptions_use_case(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
) -> GetSubscriptionsUseCase:
    return GetSubscriptionsUseCase(repository)


def get_subscription_setup_info_use_case(
    package_use_case: GetPackageUseCase = Depends(get_package_use_case),
) -> GetSubscriptionSetupInfoUseCase:
    return GetSubscriptionSetupInfoUseCase(package_use_case)
