import structlog

from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.exceptions import NotFoundException
from app.domains.agent.repository import AgentRepository
from app.domains.package.repository import AgentPackageRepository
from app.infra.external.azure.azure_resource_service import AzureResourceService

logger = structlog.get_logger()


class RequestAgentUpdateUseCase:
    """배포된 에이전트의 OTA 업데이트를 수행하는 유스케이스

    ARM API를 통해 Function App의 WEBSITE_RUN_FROM_PACKAGE 설정을 변경하여
    에이전트가 새 패키지로 자동 재시작되도록 합니다.
    """

    def __init__(
        self,
        repository: AgentRepository,
        package_repository: AgentPackageRepository,
        azure_resource_service: AzureResourceService,
    ):
        self.repository = repository
        self.package_repository = package_repository
        self.azure_resource_service = azure_resource_service

    async def execute(
        self,
        identity: Identity,
        tenant_id: str,
        agent_id: str,
        target_version: str = "latest",
    ) -> dict:
        # 1. 에이전트 조회
        agent = await self.repository.get_active_agent_by_client_id(
            tenant_id=tenant_id, agent_id=agent_id
        )
        if not agent:
            raise NotFoundException(f"에이전트를 찾을 수 없습니다: {agent_id}")

        # 2. 패키지 버전 확인
        if target_version == "latest":
            package = await self.package_repository.get_latest()
        else:
            package = await self.package_repository.get_by_version(target_version)

        if not package:
            raise NotFoundException(f"패키지를 찾을 수 없습니다: {target_version}")

        # 이미 같은 버전이면 스킵
        if agent.version == package.version:
            return {
                "success": False,
                "message": f"에이전트가 이미 최신 버전입니다: {package.version}",
                "current_version": agent.version,
                "target_version": package.version,
            }

        # 3. Azure가 직접 접근 가능한 다운로드 URL 생성
        new_package_url = await self.package_repository.generate_download_url(package.filename)

        # 4. OBO 토큰으로 ARM API 호출
        arm_token = await get_obo_access_token(identity.sso_token)

        result = await self.azure_resource_service.update_function_app_settings(
            access_token=arm_token,
            subscription_id=agent.subscription_id,
            resource_group_name=agent.resource_group_name,
            function_app_name=agent.function_app_name,
            settings_to_update={
                "WEBSITE_RUN_FROM_PACKAGE": new_package_url,
            },
        )

        logger.info(
            "Agent update requested",
            agent_id=agent_id,
            current_version=agent.version,
            target_version=package.version,
            arm_result=result,
        )

        return {
            "success": result == "SUCCESS",
            "message": (
                f"업데이트가 시작되었습니다. ({agent.version} → {package.version})"
                if result == "SUCCESS"
                else f"업데이트 요청 실패: {result}"
            ),
            "current_version": agent.version,
            "target_version": package.version,
            "arm_status": result,
        }
