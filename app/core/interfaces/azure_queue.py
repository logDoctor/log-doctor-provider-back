from abc import ABC, abstractmethod


class AzureQueueService(ABC):
    """Azure Storage Queue(Data Plane) 서비스 인터페이스"""

    @abstractmethod
    async def push(
        self,
        account_name: str,
        queue_name: str,
        message: dict,
        tenant_id: str | None = None,
    ) -> None:
        """Azure Storage Queue에 메시지를 전송합니다."""
        pass
