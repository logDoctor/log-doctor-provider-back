import structlog

from app.core.auth.models import Identity
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.interfaces.azure_arm import AzureArmService
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import AgentResponse, DeactivateAgentResponse

logger = structlog.get_logger()


class DeactivateAgentUseCase:
    """에이전트 비활성화 요청 유스케이스 (Phase 7 - 쓰기)

    Agent 엔티티의 상태를 DEACTIVATING으로 변경하고,
    Azure 리소스 그룹 삭제를 시작합니다.
    """

    def __init__(
        self,
        agent_repository: AgentRepository,
        azure_arm_service: AzureArmService,
    ):
        self.agent_repository = agent_repository
        self.azure_arm_service = azure_arm_service

    async def execute(
        self, identity: Identity, tenant_id: str, agent_id: str
    ) -> DeactivateAgentResponse:
        agent = await self.agent_repository.get_by_id(
            tenant_id=tenant_id, id=agent_id
        )
        if not agent:
            raise NotFoundException(f"Agent {agent_id} not found.")

        # 사전 권한 검증: 사용자에게 리소스 그룹 쓰기 권한이 있는지 확인
        try:
            await self.azure_arm_service.check_deployment_permission(
                identity.sso_token, agent.subscription_id
            )
        except ForbiddenException as e:
            logger.warning(
                "User lacks permission to deactivate agent",
                agent_id=agent_id,
                subscription_id=agent.subscription_id,
            )
            raise ForbiddenException(
                "AGENT_MANAGE_FORBIDDEN|You do not have sufficient permissions to deactivate this agent. Azure Contributor role is required."
            ) from e

        agent.deactivate()

        # 🚀 [ROLE CLEANUP] Resource Group 삭제 전에 Function App의 Managed Identity를 조회해 역할 할당 해제
        try:
            principal_id = await self.azure_arm_service.get_function_app_principal_id(
                access_token=identity.sso_token,
                subscription_id=agent.subscription_id,
                resource_group_name=agent.resource_group_name,
                function_app_name=agent.function_app_name
            )
            
            if principal_id:
                logger.info("Found Function App principal ID for role deletion", principal_id=principal_id)
                assignments = await self.azure_arm_service.list_role_assignments(
                    access_token=identity.sso_token,
                    subscription_id=agent.subscription_id
                )
                
                # 해당 principal_id 에 부여된 역할 할당만 골라 삭제
                for assignment in assignments:
                    props = assignment.get("properties", {})
                    if props.get("principalId") == principal_id:
                        assignment_id = assignment.get("id")
                        logger.info("Deleting subscription-level role assignment", role_assignment_id=assignment_id)
                        await self.azure_arm_service.delete_role_assignment(
                            access_token=identity.sso_token,
                            role_assignment_id=assignment_id
                        )
        except Exception as e:
            # 역할 삭제에 실패하더라도 리소스 그룹 삭제 등 메인 해제 흐름은 유지합니다.
            logger.warn("Failed to clean up role assignments for agent", agent_id=agent_id, error=str(e))

        try:
            await self.azure_arm_service.delete_resource_group(
                access_token=identity.sso_token,
                subscription_id=agent.subscription_id,
                resource_group_name=agent.resource_group_name,
            )
        except Exception as e:
            logger.error(
                "Failed to delete Azure resource group", agent_id=agent_id, error=str(e)
            )
            agent.mark_deactivate_failed()

        await self.agent_repository.upsert_agent(agent)

        return DeactivateAgentResponse(
            message=f"Deactivation request for agent {agent_id} is in progress.",
            agent=AgentResponse.model_validate(agent),
        )
