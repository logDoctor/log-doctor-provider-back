from functools import lru_cache

from fastapi import Depends

from app.core.interfaces.azure_queue import AzureQueueService
from app.domains.agent.dependencies import get_agent_repository
from app.domains.agent.repository import AgentRepository
from app.infra.db.cosmos import CosmosDB
from app.infra.external.azure.dependencies import get_azure_queue_service

from .repository import AzureReportRepository, ReportRepository
from .usecases.create_report_use_case import CreateReportUseCase


@lru_cache
async def get_report_repository() -> ReportRepository:
    container = await CosmosDB.get_container("reports")
    return AzureReportRepository(container)


@lru_cache
def get_create_report_use_case(
    report_repository: ReportRepository = Depends(get_report_repository),
    agent_repository: AgentRepository = Depends(get_agent_repository),
    azure_queue_service: AzureQueueService = Depends(get_azure_queue_service),
) -> CreateReportUseCase:
    return CreateReportUseCase(report_repository, agent_repository, azure_queue_service)
