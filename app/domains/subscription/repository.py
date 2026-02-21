from abc import ABC, abstractmethod
from azure.mgmt.subscription.aio import SubscriptionClient

from app.infra.external.azure_client import AzureRestClient, DummyCredential


# 1. Interface
class SubscriptionRepository(ABC):
    @abstractmethod
    async def list_subscriptions(self, access_token: str) -> list[dict]:
        """List Azure Subscriptions"""
        pass


# 2. Implementation
class AzureSubscriptionRepository(SubscriptionRepository):
    async def list_subscriptions(self, access_token: str) -> list[dict]:
        credential = DummyCredential(access_token)
        
        subscriptions = []
        async with SubscriptionClient(credential) as client:
            async for sub in client.subscriptions.list():
                subscriptions.append({
                    "subId": sub.id,
                    "subscriptionId": sub.subscription_id,
                    "displayName": sub.display_name,
                    "state": sub.state
                })
            
        return subscriptions
