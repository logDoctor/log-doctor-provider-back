import structlog

from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.core.interfaces.azure_arm import AzureArmService
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.schemas import AgentResponse, RequestAgentUpdateResponse
from app.domains.package.repository import AgentPackageRepository

logger = structlog.get_logger()


class RequestAgentUpdateUseCase:
    """배포된 에이전트의 OTA 업데이트를 수행하는 유스케이스

    ARM API를 통해 Function App의 WEBSITE_RUN_FROM_PACKAGE 설정을 변경하여
    에이전트가 새 패키지로 자동 재시작되도록 합니다.
    """

    def __init__(
        self,
        agent_repository: AgentRepository,
        package_repository: AgentPackageRepository,
        azure_arm_service: AzureArmService,
    ):
        self.agent_repository = agent_repository
        self.package_repository = package_repository
        self.azure_arm_service = azure_arm_service

    async def execute(
        self,
        identity: Identity,
        tenant_id: str,
        agent_id: str,
        target_version: str = "latest",
    ) -> RequestAgentUpdateResponse:
        agent = await self.agent_repository.get_by_id(tenant_id=tenant_id, id=agent_id)
        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found.")
        if agent.is_deleted():
            raise ConflictException(f"Cannot update a deleted agent: {agent_id}")

        package = await self.package_repository.get_by_version(target_version)

        if not package:
            raise NotFoundException(f"Package {target_version} not found.")

        if agent.version == package.version:
            raise ConflictException(
                f"Agent is already at the latest version ({package.version})."
            )

        new_package_url = await self.package_repository.generate_download_url(
            package.filename
        )

        # 사전 권한 검증: 사용자에게 리소스 그룹 쓰기 권한이 있는지 확인
        try:
            await self.azure_arm_service.check_deployment_permission(
                identity.sso_token, agent.subscription_id
            )
        except ForbiddenException as e:
            logger.warning(
                "User lacks permission to update agent",
                agent_id=agent_id,
                subscription_id=agent.subscription_id,
            )
            raise ForbiddenException(
                "AGENT_MANAGE_FORBIDDEN|You do not have sufficient permissions to update this agent. Azure Contributor role is required."
            ) from e

        arm_token = await get_obo_access_token(identity.sso_token)

        agent.start_update()

        success = True
        message = f"Update request successful. ({agent.version} -> {package.version})"

        try:
            await self.azure_arm_service.update_function_app_settings(
                access_token=arm_token,
                subscription_id=agent.subscription_id,
                resource_group_name=agent.resource_group_name,
                function_app_name=agent.function_app_name,
                settings_to_update={
                    "WEBSITE_RUN_FROM_PACKAGE": new_package_url,
                },
            )
        except ForbiddenException as e:
            # check_deployment_permission 외에 ARM 내부 호출 중 403이 나온 경우
            logger.error("Agent update forbidden", agent_id=agent_id, error=str(e))
            agent.mark_update_failed()
            success = False
            message = "AGENT_MANAGE_FORBIDDEN|You do not have sufficient permissions to update this agent. Azure Contributor role is required."
        except Exception as e:
            logger.error("Agent update failed", agent_id=agent_id, error=str(e))
            agent.mark_update_failed()
            success = False
            message = f"Failed to request agent update: {str(e)}"

        await self.agent_repository.upsert_agent(agent)

        return RequestAgentUpdateResponse(
            message=message,
            agent=AgentResponse.model_validate(agent),
            success=success,
        )
