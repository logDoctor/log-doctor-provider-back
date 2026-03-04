import structlog

from app.core.exceptions import NotFoundException
from app.domains.agent.repository import AgentRepository
from app.infra.external.azure_resource_service import AzureResourceService

logger = structlog.get_logger()


class CheckAzureStatusUseCase:
    """Azure 리소스 그룹 존재 여부 확인 유스케이스 (Phase 2 - 읽기)

    Managed Identity를 사용하여 순수 읽기 작업으로 수행합니다.
    DB 상태를 변경하지 않습니다.
    """

    def __init__(
        self,
        repository: AgentRepository,
        azure_resource_service: AzureResourceService,
    ):
        self.repository = repository
        self.azure_resource_service = azure_resource_service

    async def execute(self, tenant_id: str, agent_id: str) -> dict:
        # 1. 에이전트 조회
        agent = await self.repository.get_agent(tenant_id=tenant_id, agent_id=agent_id)
        if not agent:
            raise NotFoundException(f"에이전트를 찾을 수 없습니다: {agent_id}")

        # 2. Managed Identity로 리소스 그룹 존재 여부 확인
        exists = await self.azure_resource_service.check_resource_group_exists(
            subscription_id=agent.subscription_id,
            resource_group_name=agent.resource_group_name,
        )

        logger.info(
            "Azure resource group status checked",
            agent_id=agent_id,
            resource_group_name=agent.resource_group_name,
            exists=exists,
        )

        return {
            "exists": exists,
            "resource_group_name": agent.resource_group_name,
        }
