from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from .models import Notification


class NotificationRepository(ABC):
    @abstractmethod
    async def save(self, notification: Notification) -> Notification:
        """저장소에 알림 이력을 기록합니다."""
        pass

    @abstractmethod
    async def list_by_tenant(self, tenant_id: str) -> list[Notification]:
        """테넌트별 알림 이력을 조회합니다."""
        pass


@cosmos_repository(map_to=Notification)
class AzureNotificationRepository(NotificationRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def save(self, notification: Notification) -> Notification:
        return await self.container.upsert_item(body=notification.to_dict())

    async def list_by_tenant(self, tenant_id: str) -> list[Notification]:
        query = "SELECT * FROM c WHERE c.tenant_id = @tenant_id"
        parameters = [{"name": "@tenant_id", "value": tenant_id}]
        items = self.container.query_items(
            query=query, parameters=parameters
        )
        return [item async for item in items]
