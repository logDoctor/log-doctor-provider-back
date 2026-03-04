from fastapi import Depends

from app.domains.tenant.dependencies import get_tenant_repository
from app.domains.tenant.repository import TenantRepository
from app.infra.db.cosmos import CosmosDB
from app.infra.external.azure.dependencies import get_azure_resource_service
from app.infra.external.azure.azure_resource_service import AzureResourceService

from .repository import AgentRepository, AzureAgentRepository
from .usecases import (
    CheckAzureStatusUseCase,
    ConfirmAgentDeletionUseCase,
    DeactivateAgentUseCase,
    HandshakeAgentUseCase,
    ListAgentsUseCase,
    ShouldAgentRunUseCase,
    TriggerAgentAnalysisUseCase,
    UpdateAgentUseCase,
)


async def get_agent_repository() -> AgentRepository:
    container = await CosmosDB.get_container("agents")
    return AzureAgentRepository(container)


# Infra dependencies are now imported from app.infra.external.azure.dependencies


def get_handshake_agent_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    tenant_repository: TenantRepository = Depends(get_tenant_repository),
) -> HandshakeAgentUseCase:
    return HandshakeAgentUseCase(repository, tenant_repository)


def get_list_agents_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
) -> ListAgentsUseCase:
    return ListAgentsUseCase(repository)


def get_should_agent_run_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
) -> ShouldAgentRunUseCase:
    return ShouldAgentRunUseCase(repository)


def get_trigger_agent_analysis_use_case() -> TriggerAgentAnalysisUseCase:
    return TriggerAgentAnalysisUseCase()


def get_update_agent_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
) -> UpdateAgentUseCase:
    return UpdateAgentUseCase(repository)


def get_deactivate_agent_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    azure_resource_service: AzureResourceService = Depends(get_azure_resource_service),
) -> DeactivateAgentUseCase:
    return DeactivateAgentUseCase(repository, azure_resource_service)


def get_check_azure_status_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
    azure_resource_service: AzureResourceService = Depends(get_azure_resource_service),
) -> CheckAzureStatusUseCase:
    return CheckAzureStatusUseCase(repository, azure_resource_service)


def get_confirm_agent_deletion_use_case(
    repository: AgentRepository = Depends(get_agent_repository),
) -> ConfirmAgentDeletionUseCase:
    return ConfirmAgentDeletionUseCase(repository)

