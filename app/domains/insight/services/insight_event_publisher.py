import json
from typing import Any, Dict

from azure.core.exceptions import AzureError
from azure.storage.queue.aio import QueueClient

from app.core.logging import get_logger

from ..schemas import InsightEventMessage

logger = get_logger("insight_event_publisher")


class InsightEventPublisher:
    def __init__(self, connection_string: str, queue_name: str = "insight-events"):
        self.connection_string = connection_string
        self.queue_name = queue_name
        self.queue_client: Any = None

    async def _get_client(self):
        if self.queue_client is None:
            self.queue_client = QueueClient.from_connection_string(
                self.connection_string, self.queue_name
            )
        return self.queue_client

    async def publish(
        self, event_type: str, tenant_id: str, agent_id: str, report_id: str, **kwargs
    ) -> bool:
        """이벤트를 큐에 발행합니다."""
        try:
            client = await self._get_client()
            message = InsightEventMessage(
                event_type=event_type,
                tenant_id=tenant_id,
                agent_id=agent_id,
                report_id=report_id,
                **kwargs,
            )

            # 5초 가시성 지연(Deduplication window 역할을 함)
            await client.send_message(message.model_dump_json(), visibility_timeout=5)
            return True
        except Exception as e:
            logger.error(
                "failed_to_publish_insight_event",
                event_type=event_type,
                report_id=report_id,
                error=str(e),
            )
            return False

    async def close(self):
        if self.queue_client:
            await self.queue_client.close()
            self.queue_client = None
