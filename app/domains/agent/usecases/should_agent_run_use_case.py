from datetime import UTC, datetime

import structlog

from app.core.cron import CronHelper
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentPollingResponse

logger = structlog.get_logger()


class ShouldAgentRunUseCase:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    async def execute(self, tenant_id: str, agent_id: str) -> AgentPollingResponse:
        """
        에이전트의 폴링 요청에 대해 현재 시점이 분석 실행 시점인지 판단합니다.
        """
        agent = await self.repository.get_agent(tenant_id=tenant_id, agent_id=agent_id)

        if not agent:
            logger.warning(
                "Polling request from unknown agent",
                tenant_id=tenant_id,
                agent_id=agent_id,
            )
            return AgentPollingResponse(should_run=False)

        # 1. 스케줄 판단 (CronHelper 사용)
        is_run_time = False
        next_run_iso = "UNKNOWN"
        try:
            # 에이전트의 스케줄 (기본값: "0 0 * * *" - 매일 자정)
            schedule = agent.analysis_schedule
            base_time = datetime.fromisoformat(
                agent.last_handshake_at.replace("Z", "+00:00")
            )
            now = datetime.now(UTC)

            # UTC 시간 기준으로 실행 시점 판단
            is_run_time = CronHelper.is_time_to_run(
                schedule,
                base_time.replace(
                    tzinfo=None
                ),  # croniter는 naive datetime으로 처리 권장
                now.replace(tzinfo=None),
            )

            next_run = CronHelper.get_next_run(schedule, base_time.replace(tzinfo=None))
            next_run_iso = next_run.replace(tzinfo=UTC).isoformat()

            if is_run_time:
                logger.info(
                    "Agent analysis scheduled run detected",
                    agent_id=agent_id,
                    next_run=next_run_iso,
                )

        except Exception as e:
            logger.error(
                "Error parsing cron schedule",
                schedule=agent.analysis_schedule,
                error=str(e),
            )

        # 2. 결과 반환
        return AgentPollingResponse(
            should_run=is_run_time,
            command="ANALYZE" if is_run_time else None,
            params={
                "current_schedule": agent.analysis_schedule,
                "next_run_estimated": next_run_iso if not is_run_time else "NOW",
            },
        )
