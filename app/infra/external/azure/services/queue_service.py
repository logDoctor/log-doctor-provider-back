import json

import structlog
from azure.core.credentials import TokenCredential

from app.core.interfaces.azure_queue import AzureQueueService
from app.infra.external.azure.clients import AzureQueueClient


class AzureQueueServiceImpl(AzureQueueService):
    """Azure Storage Queue 기반 서비스 구현체"""

    def __init__(
        self,
        credential: TokenCredential,
        queue_client: AzureQueueClient,
        logger: structlog.BoundLogger,
    ):
        self.credential = credential
        self.queue_client = queue_client
        self.logger = logger

    async def push(self, account_name: str, queue_name: str, message: dict) -> None:
        """DefaultAzureCredential을 사용하여 Azure Storage Queue에 메시지를 전송합니다."""
        async with self.queue_client.get_queue_client(
            account_name=account_name,
            queue_name=queue_name,
            credential=self.credential,
        ) as client:
            await client.send_message(json.dumps(message))
