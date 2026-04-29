import structlog

from app.core.exceptions import NotFoundException
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.repositories import ScheduleRepository
from app.domains.agent.schemas import AgentResponse, ConfirmAgentDeletionResponse

logger = structlog.get_logger()


class ConfirmAgentDeletionUseCase:
    def __init__(
        self,
        agent_repository: AgentRepository,
        schedule_repository: ScheduleRepository,
    ):
        self.agent_repository = agent_repository
        self.schedule_repository = schedule_repository

    async def execute(
        self, tenant_id: str, agent_id: str
    ) -> ConfirmAgentDeletionResponse:
        """
        Azure 리소스 그룹이 삭제된 것을 프론트엔드가 확인한 후 호출합니다.
        비즈니스 규칙 및 상태 전이는 Agent 엔티티 내부에서 처리합니다.

        트랜잭션 순서:
          1. Agent 상태 변경 → upsert (critical)
          2. Schedule 비활성화 (best-effort: 실패해도 타이머가 can_start_analysis()로 방어)
        """
        agent = await self.agent_repository.get_by_id(tenant_id=tenant_id, id=agent_id)
        if not agent:
            raise NotFoundException(f"Agent not found: {agent_id}")

        agent.confirm_deletion()
        await self.agent_repository.upsert_agent(agent)

        try:
            await self.schedule_repository.disable_by_agent(agent_id)
        except Exception as e:
            logger.warning(
                "Failed to disable schedules after deletion — timer will handle via can_start_analysis()",
                agent_id=agent_id,
                error=str(e),
            )

        return ConfirmAgentDeletionResponse(
            message=f"Agent {agent_id} has been marked as DELETED.",
            agent=AgentResponse.model_validate(agent),
        )
