from abc import ABC, abstractmethod

from app.infra.external.azure.clients import AzureArmClient


class SubscriptionRepository(ABC):
    @abstractmethod
    async def list_subscriptions(self, access_token: str) -> list[dict]:
        """Azure 구독 목록을 조회합니다."""
        pass


class AzureSubscriptionRepository(SubscriptionRepository):
    def __init__(self, arm_client: AzureArmClient):
        self.arm_client = arm_client

    async def list_subscriptions(self, access_token: str) -> list[dict]:
        url = "/subscriptions?api-version=2020-01-01"

        async with self.arm_client.get_client(access_token) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])
