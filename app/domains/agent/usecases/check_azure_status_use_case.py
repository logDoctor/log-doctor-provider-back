import structlog

from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.exceptions import NotFoundException
from app.domains.agent.repository import AgentRepository
from app.infra.external.azure.azure_resource_service import AzureResourceService

logger = structlog.get_logger()


class CheckAzureStatusUseCase:
    """Azure 리소스 그룹 존재 여부 확인 유스케이스 (Phase 2 - 읽기)

    OBO 토큰을 사용하여 사용자의 권한으로 리소스 그룹 존재 여부를 확인합니다.
    DB 상태를 변경하지 않습니다.
    """

    def __init__(
        self,
        repository: AgentRepository,
        azure_resource_service: AzureResourceService,
    ):
        self.repository = repository
        self.azure_resource_service = azure_resource_service

    async def execute(self, identity: Identity, tenant_id: str, agent_id: str) -> dict:
        # 1. 에이전트 조회
        agent = await self.repository.get_active_agent_by_client_id(tenant_id=tenant_id, agent_id=agent_id)
        if not agent:
            raise NotFoundException(f"에이전트를 찾을 수 없습니다: {agent_id}")

        # 2. OBO 토큰 교환 (사용자 권한으로 읽기 위해)
        arm_token = await get_obo_access_token(identity.sso_token)

        # 3. ARM 토큰으로 리소스 그룹 존재 여부 확인
        exists = await self.azure_resource_service.check_resource_group_exists(
            access_token=arm_token,
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
