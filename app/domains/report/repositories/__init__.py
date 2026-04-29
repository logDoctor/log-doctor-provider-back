from app.infra.db.cosmos import CosmosDB

from .diagnosis import AzureDiagnosisRepository, DiagnosisRepository
from .report import AzureReportRepository, ReportRepository

__all__ = [
    "ReportRepository",
    "AzureReportRepository",
    "DiagnosisRepository",
    "AzureDiagnosisRepository",
    "get_report_repository",
    "get_diagnosis_repository",
]


async def get_report_repository() -> ReportRepository:
    container = await CosmosDB.get_container("reports")
    return AzureReportRepository(container)


async def get_diagnosis_repository() -> DiagnosisRepository:
    container = await CosmosDB.get_container("diagnoses")
    return AzureDiagnosisRepository(container)
