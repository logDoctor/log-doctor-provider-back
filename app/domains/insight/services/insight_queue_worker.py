import asyncio
import json
from typing import Any, Optional

from azure.storage.queue.aio import QueueClient

from app.core.logging import get_logger
from app.domains.report.repositories import ReportRepository

from ..schemas import InsightEventMessage
from ..usecases.recalculate_metrics_use_case import RecalculateMetricsUseCase
from ..usecases.update_insight_use_case import UpdateInsightUseCase

logger = get_logger("insight_queue_worker")


class InsightQueueWorker:
    def __init__(
        self,
        connection_string: str,
        update_use_case: UpdateInsightUseCase,
        recalculate_use_case: RecalculateMetricsUseCase,
        queue_name: str = "insight-events",
    ):
        self.connection_string = connection_string
        self.queue_name = queue_name
        self.update_use_case = update_use_case
        self.recalculate_use_case = recalculate_use_case
        self.queue_client: Optional[QueueClient] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if self._running:
            return

        self._running = True
        self.queue_client = QueueClient.from_connection_string(
            self.connection_string, self.queue_name
        )
        self._task = asyncio.create_task(self._run())
        logger.info("insight_worker_started")

    async def stop(self):
        self._running = False
        if self._task:
            await self._task
        if self.queue_client:
            await self.queue_client.close()
        logger.info("insight_worker_stopped")

    async def _run(self):
        while self._running:
            try:
                # receive_messages는 비동기 이터레이터를 반환하므로 await을 붙이지 않습니다.
                messages = self.queue_client.receive_messages(
                    max_messages=10, visibility_timeout=30
                )
                
                count = 0
                async for msg in messages:
                    count += 1
                    try:
                        await self._process_message(msg)
                        await self.queue_client.delete_message(msg)
                    except Exception as e:
                        logger.error(
                            "failed_to_process_insight_message",
                            message_id=msg.id,
                            error=str(e),
                            dequeue_count=msg.dequeue_count,
                        )
                
                if count == 0:
                    await asyncio.sleep(5)
                    continue
                        # 5회 이상 실패 시 Poison Queue 처리는 Azure 기본 기능을 활용하거나
                        # 여기서 직접 구현할 수 있습니다.

            except Exception as e:
                logger.error("insight_worker_loop_error", error=str(e))
                await asyncio.sleep(10)

    async def _process_message(self, msg: Any):
        data = json.loads(msg.content)
        event = InsightEventMessage(**data)

        logger.info(
            "processing_insight_event",
            event_type=event.event_type,
            agent_id=event.agent_id,
        )

        if event.event_type == "report_completed":
            # 리포트 정보가 필요하므로 Repository에서 조회 (UseCase 내부에서 처리 권장)
            # 여기서는 편의상 Worker가 직접 UseCase를 호출하도록 구현
            # TODO: UpdateInsightUseCase에 report_id만 넘기고 내부에서 조회하도록 수정 가능
            from app.domains.report.repositories import AzureReportRepository  # 임시

            # 실제 구현 시에는 DI된 repository 사용
            report = await self.recalculate_use_case.report_repository.get_by_id(
                event.tenant_id, event.report_id
            )
            if report:
                await self.update_use_case.execute(
                    event.tenant_id, event.agent_id, report
                )

        elif event.event_type == "diagnosis_resolved":
            await self.recalculate_use_case.execute(
                event.tenant_id, event.agent_id, event.report_id
            )
