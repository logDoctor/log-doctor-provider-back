from fastapi import Depends

from app.core.auth.dependencies import get_graph_service
from app.core.auth.services.graph_service import GraphService
from app.core.interfaces.azure_arm import AzureArmService
from app.core.interfaces.azure_queue import AzureQueueService
from app.domains.package.dependencies import get_agent_package_repository
from app.domains.package.repository import AgentPackageRepository
from app.domains.report.repositories import get_report_repository
from app.domains.report.repositories.report import ReportRepository
from app.domains.tenant.dependencies import (
    get_subscription_repository,
    get_tenant_repository,
)
from app.domains.tenant.repositories import SubscriptionRepository, TenantRepository
from app.infra.external.azure.dependencies import (
    get_azure_arm_service,
    get_azure_queue_service,
)

from .repositories import (
    AgentIssueRepository,
    AgentRepository,
    ScheduleRepository,
    get_agent_issue_repository,
    get_agent_repository,
    get_schedule_repository,
)
from .usecases import (
    CheckAzureResourceGroupStatusUseCase,
    ConfirmAgentDeletionUseCase,
    CreateScheduleUseCase,
    DeactivateAgentUseCase,
    DeleteScheduleUseCase,
    DiscoverAgentResourcesUseCase,
    HandshakeAgentUseCase,
    ListSchedulesUseCase,
    PlatformAdminListAgentsUseCase,
    PokeAgentUseCase,
    RequestAgentUpdateUseCase,
    TenantAdminUninstallUseCase,
    TenantUserListAgentsUseCase,
    TriggerScheduledRunUseCase,
    UpdateAgentUseCase,
    UpdateScheduleUseCase,
)
from .usecases.report_agent_issue import ReportAgentIssueUseCase


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
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
) -> TenantUserListAgentsUseCase:
    return TenantUserListAgentsUseCase(
        repository, subscription_repository, tenant_repository, azure_arm_service
    )


def get_platform_admin_list_agents_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
) -> PlatformAdminListAgentsUseCase:
    return PlatformAdminListAgentsUseCase(repository)


def get_deactivate_agent_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
) -> DeactivateAgentUseCase:
    return DeactivateAgentUseCase(repository, azure_arm_service, schedule_repository)


def get_check_azure_resource_group_status_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
) -> CheckAzureResourceGroupStatusUseCase:
    return CheckAzureResourceGroupStatusUseCase(repository, azure_arm_service)


def get_confirm_agent_deletion_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
) -> ConfirmAgentDeletionUseCase:
    return ConfirmAgentDeletionUseCase(repository, schedule_repository)


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
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
) -> TenantAdminUninstallUseCase:
    return TenantAdminUninstallUseCase(
        tenant_repository, agent_repository, azure_arm_service, schedule_repository
    )


def get_update_agent_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    graph_service: GraphService = Depends(get_graph_service),
) -> UpdateAgentUseCase:
    return UpdateAgentUseCase(repository, graph_service)


def get_report_agent_issue_use_case(
    repository: AgentIssueRepository = Depends(get_agent_issue_repository),
) -> ReportAgentIssueUseCase:
    return ReportAgentIssueUseCase(repository)


# --- Schedule factories ---


def get_list_schedules_use_case(
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
    agent_repository: AgentRepository = Depends(get_agent_repository),
) -> ListSchedulesUseCase:
    return ListSchedulesUseCase(schedule_repository, agent_repository)


def get_create_schedule_use_case(
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
    agent_repository: AgentRepository = Depends(get_agent_repository),
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
    package_repository: AgentPackageRepository = Depends(get_agent_package_repository),
) -> CreateScheduleUseCase:
    return CreateScheduleUseCase(
        schedule_repository, agent_repository, azure_arm_service, package_repository
    )


def get_update_schedule_use_case(
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
    agent_repository: AgentRepository = Depends(get_agent_repository),
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
    package_repository: AgentPackageRepository = Depends(get_agent_package_repository),
) -> UpdateScheduleUseCase:
    return UpdateScheduleUseCase(
        schedule_repository, agent_repository, azure_arm_service, package_repository
    )


def get_delete_schedule_use_case(
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
) -> DeleteScheduleUseCase:
    return DeleteScheduleUseCase(schedule_repository)


def get_trigger_scheduled_run_use_case(
    schedule_repository: ScheduleRepository = Depends(get_schedule_repository),
    report_repository: ReportRepository = Depends(get_report_repository),
    agent_repository: AgentRepository = Depends(get_agent_repository),
    azure_queue_service: AzureQueueService = Depends(get_azure_queue_service),
    package_repository: AgentPackageRepository = Depends(get_agent_package_repository),
) -> TriggerScheduledRunUseCase:
    return TriggerScheduledRunUseCase(
        schedule_repository,
        report_repository,
        agent_repository,
        azure_queue_service,
        package_repository,
    )


def get_discover_agent_resources_use_case(
    azure_arm_service: AzureArmService = Depends(get_azure_arm_service),
    agent_repository: AgentRepository = Depends(get_agent_repository),
) -> DiscoverAgentResourcesUseCase:
    return DiscoverAgentResourcesUseCase(azure_arm_service, agent_repository)


def get_poke_agent_use_case(
    azure_queue_service: AzureQueueService = Depends(get_azure_queue_service),
) -> PokeAgentUseCase:
    return PokeAgentUseCase(azure_queue_service)
