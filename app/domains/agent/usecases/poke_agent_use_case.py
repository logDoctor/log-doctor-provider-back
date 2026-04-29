import structlog

from app.core.interfaces.azure_queue import AzureQueueService

logger = structlog.get_logger(__name__)


class PokeAgentUseCase:
    def __init__(self, queue_service: AzureQueueService):
        self.queue_service = queue_service

    async def execute(self, storage_account_name: str, subscription_id: str) -> bool:
        """
        특정 에이전트의 큐에 메시지를 보내 즉시 기상(Wake-up)시킵니다.
        """
        try:
            # 큐 메시지 전송 (빈 메시지여도 QueueTrigger가 작동함)
            # 큐 이름은 Bicep에 정의된 'diagnosis-requests' 사용
            await self.queue_service.push(
                storage_account_name=storage_account_name,
                queue_name="diagnosis-requests",
                subscription_id=subscription_id,
                message={"command": "WAKE_UP"},
            )
            logger.info(
                "poked_agent_successfully", storage_account_name=storage_account_name
            )
            return True
        except Exception as e:
            logger.error(
                "failed_to_poke_agent",
                storage_account_name=storage_account_name,
                error=str(e),
            )
            return False
