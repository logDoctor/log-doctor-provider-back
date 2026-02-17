from abc import ABC, abstractmethod

from app.infra.external.azure_client import AzureRestClient


# 1. Interface
class SubscriptionRepository(ABC):
    @abstractmethod
    async def list_subscriptions(self, access_token: str) -> list[dict]:
        """List Azure Subscriptions"""
        pass


# 2. Implementation
class AzureSubscriptionRepository(SubscriptionRepository):
    async def list_subscriptions(self, access_token: str) -> list[dict]:
        url = "/subscriptions?api-version=2020-01-01"

        async with AzureRestClient.get_client(access_token) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])
