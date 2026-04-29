import structlog
from app.core.config import settings
from app.core.interfaces.azure_arm import AzureArmService
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.models import AgentStatus
from app.domains.agent.schemas.agent import DiscoveredAzureResource

logger = structlog.get_logger(__name__)


class DiscoverAgentResourcesUseCase:
    def __init__(self, arm_service: AzureArmService, agent_repository: AgentRepository):
        self.arm_service = arm_service
        self.agent_repository = agent_repository

    async def execute(
        self, sso_token: str, subscription_id: str, tenant_id: str
    ) -> list[DiscoveredAzureResource]:
        """
        사용자의 Azure 구독에서 에이전트 리소스를 탐색합니다.

        1. 제약 조건 확인: 해당 구독에 이미 활성 에이전트가 있는지 체크합니다.
        2. ARM API를 사용하여 특정 태그가 붙은 리소스를 조회합니다.
        3. 조회된 리소스를 최신 생성일 순으로 정렬하여 반환합니다.
        """
        # 1. 해당 구독에 이미 활성(ACTIVE) 상태인 에이전트가 있는지 확인
        active_agent = await self.agent_repository.get_agent_by_subscription(
            subscription_id=subscription_id, statuses=[AgentStatus.ACTIVE]
        )

        if active_agent:
            logger.info(
                "active_agent_already_exists_for_subscription",
                subscription_id=subscription_id,
            )
            return []

        # 2. 태그 기반 리소스 조회
        resources = await self.arm_service.list_resources_by_tag(
            access_token=sso_token,
            subscription_id=subscription_id,
            tag_name=settings.AGENT_TAG_NAME,
            tag_value=settings.AGENT_TAG_VALUE,
        )

        # 3. 최신 생성일 순으로 정렬
        resources.sort(key=lambda x: x.get("createdTime", ""), reverse=True)

        # 4. 등록 여부 대조를 위한 준비
        registered_storage_names = await self._get_registered_storage_names(tenant_id)

        # 5. 리소스 정보 정리 및 매핑 (Schema 객체로 변환)
        return [
            self._map_resource_to_schema(resource, registered_storage_names)
            for resource in resources
            if resource.get("name")
        ]

    async def _get_registered_storage_names(self, tenant_id: str) -> set[str]:
        """현재 DB에 등록된 에이전트들의 스토리지 계정 이름 집합을 반환합니다."""
        existing_agents = await self.agent_repository.get_all_by_tenant_id(tenant_id)
        return {
            a.storage_account_name for a in existing_agents if a.storage_account_name
        }

    def _map_resource_to_schema(
        self, resource: dict, registered_storage_names: set[str]
    ) -> DiscoveredAzureResource:
        """Azure 리소스 정보를 DiscoveredAzureResource 스키마 객체로 변환합니다."""
        storage_account_name = resource.get("name", "")
        resource_id = resource.get("id", "")

        # 리소스 ID에서 리소스 그룹 추출
        resource_group = "unknown"
        if "/resourceGroups/" in resource_id:
            resource_group = resource_id.split("/resourceGroups/")[1].split("/")[0]

        return DiscoveredAzureResource(
            storage_account_name=storage_account_name,
            resource_group=resource_group,
            location=resource.get("location", ""),
            is_registered=storage_account_name in registered_storage_names,
            resource_id=resource_id,
            created_at=resource.get("createdTime"),
        )
