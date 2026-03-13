from fastapi import Depends

from app.core.interfaces.azure_queue import AzureQueueService
from app.domains.agent.dependencies import get_agent_repository
from app.domains.agent.repository import AgentRepository
from app.domains.notification.dependencies import get_notification_service
from app.domains.notification.service import NotificationService
from app.infra.db.cosmos import CosmosDB
from app.infra.external.azure.dependencies import get_azure_queue_service

from .repository import (
    AzureDiagnosisRepository,
    AzureReportRepository,
    DiagnosisRepository,
    ReportRepository,
)
from .usecases import (
    CreateReportUseCase,
    GetReportUseCase,
    ListReportsUseCase,
    ReceiveDiagnosesUseCase,
    UpdateDiagnosisResolutionUseCase,
    UpdateReportStatusUseCase,
)


async def get_report_repository() -> ReportRepository:
    container = await CosmosDB.get_container("reports")
    return AzureReportRepository(container)


async def get_create_report_use_case(
    report_repository: ReportRepository = Depends(get_report_repository),
    agent_repository: AgentRepository = Depends(get_agent_repository),
    azure_queue_service: AzureQueueService = Depends(get_azure_queue_service),
) -> CreateReportUseCase:
    return CreateReportUseCase(
        report_repository,
        agent_repository,
        azure_queue_service,
    )


async def get_diagnosis_repository() -> DiagnosisRepository:
    container = await CosmosDB.get_container("diagnoses")
    return AzureDiagnosisRepository(container)


async def get_get_report_use_case(
    report_repository: ReportRepository = Depends(get_report_repository),
    diagnosis_repository: DiagnosisRepository = Depends(get_diagnosis_repository),
) -> GetReportUseCase:
    return GetReportUseCase(report_repository, diagnosis_repository)


def get_list_reports_use_case(
    report_repository: ReportRepository = Depends(get_report_repository),
) -> ListReportsUseCase:
    return ListReportsUseCase(report_repository)


def get_receive_diagnoses_use_case(
    diagnosis_repository: DiagnosisRepository = Depends(get_diagnosis_repository),
) -> ReceiveDiagnosesUseCase:
    return ReceiveDiagnosesUseCase(diagnosis_repository)


def get_update_report_status_use_case(
    report_repository: ReportRepository = Depends(get_report_repository),
    notification_service: NotificationService = Depends(get_notification_service),
) -> UpdateReportStatusUseCase:
    return UpdateReportStatusUseCase(report_repository, notification_service)


def get_update_diagnosis_resolution_use_case(
    diagnosis_repository: DiagnosisRepository = Depends(get_diagnosis_repository),
) -> UpdateDiagnosisResolutionUseCase:
    return UpdateDiagnosisResolutionUseCase(diagnosis_repository)
