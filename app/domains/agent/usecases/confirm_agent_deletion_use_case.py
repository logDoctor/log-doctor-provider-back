import structlog

from app.domains.agent.models import AgentStatus
from app.domains.agent.repository import AgentRepository

logger = structlog.get_logger()


class ConfirmAgentDeletionUseCase:
    """에이전트 삭제 확정 유스케이스 (Phase 2 - 쓰기)

    Azure 리소스 그룹이 삭제된 것을 프론트엔드가 확인한 후 호출합니다.
    에이전트를 최종 DELETED 상태로 전환합니다.
    """

    def __init__(self, repository: AgentRepository):
        self.repository = repository

    async def execute(self, tenant_id: str, agent_id: str) -> dict:
        # 1. 에이전트 조회
        agent = await self.repository.get_active_agent_by_client_id(tenant_id=tenant_id, agent_id=agent_id)
        if not agent:
            raise NotFoundException(f"에이전트를 찾을 수 없습니다: {agent_id}")

        # 2. DEACTIVATING 상태가 아니면 확정 불가
        if agent.status == AgentStatus.DELETED:
            return {
                "confirmed": True,
                "message": "에이전트가 이미 삭제 완료 상태입니다.",
            }

        if agent.status != AgentStatus.DEACTIVATING:
            return {
                "confirmed": False,
                "message": f"에이전트가 {AgentStatus.DEACTIVATING.value} 상태가 아닙니다. 현재 상태: {agent.status.value}",
            }

        # 3. 삭제 확정
        agent.confirm_deletion()
        await self.repository.upsert_agent(agent.to_dict())

        logger.info(
            "Agent deletion confirmed",
            agent_id=agent_id,
            deleted_at=agent.deleted_at,
        )

        return {
            "confirmed": True,
            "message": "에이전트 삭제가 확정되었습니다.",
        }
