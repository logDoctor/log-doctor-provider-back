import structlog

from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.exceptions import NotFoundException
from app.domains.agent.models import AgentStatus
from app.domains.agent.repository import AgentRepository
from app.infra.external.azure.azure_resource_service import AzureResourceService

logger = structlog.get_logger()


class DeactivateAgentUseCase:
    """에이전트 비활성화 유스케이스 (Phase 1)

    OBO 토큰으로 Azure 리소스 그룹 삭제 요청을 보내고,
    에이전트를 DEACTIVATING 상태로 전환합니다.
    """

    def __init__(
        self,
        repository: AgentRepository,
        azure_resource_service: AzureResourceService,
    ):
        self.repository = repository
        self.azure_resource_service = azure_resource_service

    async def execute(
        self,
        identity: Identity,
        tenant_id: str,
        agent_id: str,
        delete_azure_resources: bool = True,
    ) -> dict:
        # 1. 에이전트 조회
        agent = await self.repository.get_active_agent_by_client_id(tenant_id=tenant_id, agent_id=agent_id)
        if not agent:
            raise NotFoundException(f"에이전트를 찾을 수 없습니다: {agent_id}")

        # 2. 이미 비활성화 중이거나 삭제된 경우
        if agent.status in (AgentStatus.DEACTIVATING, AgentStatus.DELETED):
            return {
                "success": True,
                "message": f"에이전트가 이미 {agent.status.value} 상태입니다.",
                "azure_status": "SKIPPED",
            }

        # 3. Azure 리소스 그룹 삭제 요청
        azure_status = "SKIPPED"
        if delete_azure_resources:
            # OBO 토큰 교환
            arm_token = await get_obo_access_token(identity.sso_token)

            azure_status = await self.azure_resource_service.delete_resource_group(
                access_token=arm_token,
                subscription_id=agent.subscription_id,
                resource_group_name=agent.resource_group_name,
            )

            if azure_status == "FAILED":
                agent.mark_deactivate_failed()
                await self.repository.upsert_agent(agent.to_dict())
                return {
                    "success": False,
                    "message": "Azure 리소스 그룹 삭제 요청에 실패했습니다.",
                    "azure_status": azure_status,
                }

        # 4. 에이전트 상태 전환
        if azure_status == "NOT_FOUND":
            # 리소스 그룹이 이미 없으므로 바로 DELETED 처리
            agent.confirm_deletion()
        else:
            agent.deactivate()

        await self.repository.upsert_agent(agent.to_dict())

        logger.info(
            "Agent deactivation initiated",
            agent_id=agent_id,
            azure_status=azure_status,
            new_status=agent.status,
        )

        return {
            "success": True,
            "message": "에이전트 비활성화가 시작되었습니다.",
            "azure_status": azure_status,
        }
