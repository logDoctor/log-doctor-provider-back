from fastapi import Depends

from app.core.interfaces.azure_arm import AzureArmService
from app.domains.package.dependencies import get_agent_package_repository
from app.domains.package.repository import AgentPackageRepository
from app.domains.tenant.dependencies import (
    get_subscription_repository,
    get_tenant_repository,
)
from app.domains.tenant.repositories import SubscriptionRepository, TenantRepository
from app.infra.db.cosmos import CosmosDB
from app.infra.external.azure.dependencies import get_azure_arm_service

from .repository import AgentRepository, AzureAgentRepository
from .usecases import (
    CheckAzureResourceGroupStatusUseCase,
    ConfirmAgentDeletionUseCase,
    DeactivateAgentUseCase,
    HandshakeAgentUseCase,
    PlatformAdminListAgentsUseCase,
    RequestAgentUpdateUseCase,
    TenantAdminUninstallUseCase,
    TenantUserListAgentsUseCase,
    UpdateAgentUseCase,
)


async def get_agent_repository() -> AgentRepository:
    container = await CosmosDB.get_container("agents")
    return AzureAgentRepository(container)


def get_handshake_agent_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> HandshakeAgentUseCase:
    return HandshakeAgentUseCase(repository, tenant_repository)


def get_tenant_user_list_agents_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    subscription_repository: SubscriptionRepository = Depends(
        get_subscription_repository
    ),
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantUserListAgentsUseCase:
    return TenantUserListAgentsUseCase(
        repository, subscription_repository, tenant_repository
    )


def get_platform_admin_list_agents_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
) -> PlatformAdminListAgentsUseCase:
    return PlatformAdminListAgentsUseCase(repository)


def get_deactivate_agent_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
) -> DeactivateAgentUseCase:
    return DeactivateAgentUseCase(repository, azure_arm_service)


def get_check_azure_resource_group_status_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
) -> CheckAzureResourceGroupStatusUseCase:
    return CheckAzureResourceGroupStatusUseCase(repository, azure_arm_service)


def get_confirm_agent_deletion_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
) -> ConfirmAgentDeletionUseCase:
    return ConfirmAgentDeletionUseCase(repository)


def get_request_agent_update_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    package_repository: AgentPackageRepository = Depends(get_agent_package_repository),
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
) -> RequestAgentUpdateUseCase:
    return RequestAgentUpdateUseCase(repository, package_repository, azure_arm_service)


def get_tenant_admin_uninstall_use_case(
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
    agent_repository: AgentRepository = Depends(get_agent_repository),
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
) -> TenantAdminUninstallUseCase:
    return TenantAdminUninstallUseCase(
        tenant_repository, agent_repository, azure_arm_service
    )


def get_update_agent_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
) -> UpdateAgentUseCase:
    return UpdateAgentUseCase(repository)

from .repository import AgentIssueRepository, AzureAgentIssueRepository
from .usecases.report_agent_issue import ReportAgentIssueUseCase

async def get_agent_issue_repository() -> AgentIssueRepository:
    container = await CosmosDB.get_container("agent_issues")
    return AzureAgentIssueRepository(container)

def get_report_agent_issue_use_case(
    repository: AgentIssueRepository = Depends(get_agent_issue_repository)
) -> ReportAgentIssueUseCase:
    return ReportAgentIssueUseCase(repository)
