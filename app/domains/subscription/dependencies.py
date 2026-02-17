from fastapi import Depends

from .repository import AzureSubscriptionRepository, SubscriptionRepository
from .services import SubscriptionFetcher


def get_subscription_repository() -> SubscriptionRepository:
    return AzureSubscriptionRepository()


def get_subscription_fetcher(
    repository: SubscriptionRepository = Depends(get_subscription_repository),
) -> SubscriptionFetcher:
    return SubscriptionFetcher(repository)
