import structlog

from app.domains.agent.schemas import AgentTriggerRequest, AgentTriggerResponse

logger = structlog.get_logger()


class TriggerAgentAnalysisUseCase:
    async def execute(self, request: AgentTriggerRequest) -> AgentTriggerResponse:
        """
        특정 에이전트의 로그 분석을 즉시 트리거하기 위해 고객사 Queue에 메시지를 전송합니다.
        """
        logger.info(
            "Triggering agent analysis on-demand",
            tenant_id=request.tenant_id,
            agent_id=request.agent_id,
        )

        # TODO: 실제 환경에서는 테넌트별 Storage Connection String을 DB에서 조회해야 함
        # 현재는 아키텍처 검증을 위한 시뮬레이션 로직

        try:
            # 시뮬레이션: 실제로는 QueueClient를 사용하여 메시지 전송
            # queue_client = QueueClient.from_connection_string(conn_str, "analysis-requests")
            # await queue_client.send_message(json.dumps({"command": "ANALYZE", "params": request.params}))

            logger.info(
                "Trigger message sent to queue successfully",
                queue_name="analysis-requests",
            )

            return AgentTriggerResponse(
                success=True,
                message=f"Analysis trigger sent to agent {request.agent_id} via queue (Simulated).",
            )
        except Exception as e:
            logger.error("Failed to send trigger message", error=str(e))
            return AgentTriggerResponse(
                success=False, message=f"Failed to trigger agent: {str(e)}"
            )
