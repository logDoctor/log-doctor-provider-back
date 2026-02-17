from fastapi import Depends

from .repository import AzureSubscriptionRepository, SubscriptionRepository
from .usecases.get_subscriptions_use_case import GetSubscriptionsUseCase


def get_subscription_repository() -> SubscriptionRepository:
    return AzureSubscriptionRepository()


def get_subscriptions_use_case(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
) -> GetSubscriptionsUseCase:
    return GetSubscriptionsUseCase(repository)
