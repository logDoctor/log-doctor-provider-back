import structlog

from app.core.auth import get_token_provider
from app.core.interfaces.azure_arm import AzureArmService
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import TenantAdminUninstallResponse
from app.domains.tenant.repositories import TenantRepository

logger = structlog.get_logger()


# TODO: 리팩토링 필요
class TenantAdminUninstallUseCase:
    """
    관리자가 Teams 앱을 제거했을 때 트리거되는 유스케이스입니다. (Phase 8)
    해당 테넌트의 모든 활성 에이전트와 Azure 리소스 그룹을 삭제합니다.
    """

    def __init__(
        self,
        tenant_repository: TenantRepository,
        agent_repository: AgentRepository,
        azure_arm_service: AzureArmService,
    ):
        self.tenant_repository = tenant_repository
        self.agent_repository = agent_repository
        self.azure_arm_service = azure_arm_service

    async def execute(
        self, tenant_id: str, user_id: str
    ) -> TenantAdminUninstallResponse:
        # 1. 테넌트 조회 및 관리자 확인
        tenant = await self.tenant_repository.get_by_id(tenant_id)
        if not tenant:
            logger.warning("Tenant not found for uninstall event", tenant_id=tenant_id)
            return TenantAdminUninstallResponse(
                success=False, action="TENANT_NOT_FOUND"
            )

        is_privileged = any(
            acc.get("user_id") == user_id for acc in tenant.privileged_accounts
        )
        if not is_privileged:
            logger.info(
                "Non-admin user uninstalled the app. Skipping resource cleanup.",
                tenant_id=tenant_id,
                user_id=user_id,
            )
            return TenantAdminUninstallResponse(
                success=True, action="SKIPPED_NON_ADMIN"
            )

        logger.info(
            "Admin uninstalled the app. Initiating full resource cleanup.",
            tenant_id=tenant_id,
            user_id=user_id,
        )

        # 2. 테넌트에 속한 모든 활성 에이전트 조회
        agents = await self.agent_repository.get_all_by_tenant_id(tenant_id)
        if not agents:
            logger.info(
                "No active agents found for tenant. Cleanup finished.",
                tenant_id=tenant_id,
            )
            return TenantAdminUninstallResponse(success=True, action="NO_AGENTS_FOUND")

        # 3. Azure 리소스 삭제를 위한 앱 전용 토큰 획득
        token_provider = get_token_provider()
        app_token = await token_provider.get_app_token(tid=tenant_id)

        # 4. 각 에이전트 리소스 삭제 트리거
        results = []
        for agent in agents:
            logger.info(
                "Triggering resource group deletion for agent",
                agent_id=agent.agent_id,
                rg=agent.resource_group_name,
            )

            # 리소스 삭제 (백엔드 권한 사용)
            try:
                await self.azure_arm_service.delete_resource_group(
                    access_token=app_token,
                    subscription_id=agent.subscription_id,
                    resource_group_name=agent.resource_group_name,
                )
                azure_status = "SUCCESS"
                agent.deactivate()
            except Exception as e:
                logger.error(
                    "Failed to delete resource group during uninstall",
                    agent_id=agent.agent_id,
                    error=str(e),
                )
                azure_status = "FAILED"
                agent.deactivate()  # Even if ARM fails, we deactivate locally

            await self.agent_repository.upsert_agent(agent.to_dict())
            results.append({"agent_id": agent.agent_id, "azure_status": azure_status})

        return TenantAdminUninstallResponse(
            success=True,
            action="CLEANUP_COMPLETED",
            tenant_id=tenant_id,
            results=results,
        )
