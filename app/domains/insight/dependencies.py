from fastapi import Depends

from app.core.config import settings
from app.domains.report.repositories import (
    get_diagnosis_repository,
    get_report_repository,
)
from app.infra.db.cosmos import CosmosDB

from .repositories.azure_insight_repository import AzureInsightRepository
from .services.insight_event_publisher import InsightEventPublisher
from .usecases.get_active_risks_use_case import GetActiveRisksUseCase
from .usecases.get_insight_use_case import GetInsightUseCase
from .usecases.rebuild_insight_use_case import RebuildInsightUseCase
from .usecases.recalculate_metrics_use_case import RecalculateMetricsUseCase
from .usecases.update_insight_use_case import UpdateInsightUseCase


async def get_insight_repository():
    client = await CosmosDB.get_client()
    return AzureInsightRepository(client, settings.COSMOS_DATABASE)


async def get_insight_publisher():
    return InsightEventPublisher(settings.AZURE_STORAGE_CONNECTION_STRING)


async def get_update_insight_use_case(repo=Depends(get_insight_repository)):
    return UpdateInsightUseCase(repo)


async def get_get_insight_use_case(repo=Depends(get_insight_repository)):
    return GetInsightUseCase(repo)


async def get_rebuild_insight_use_case(
    insight_repo=Depends(get_insight_repository),
    report_repo=Depends(get_report_repository),
    update_use_case=Depends(get_update_insight_use_case),
):
    return RebuildInsightUseCase(insight_repo, report_repo, update_use_case)


async def get_recalculate_metrics_use_case(
    insight_repo=Depends(get_insight_repository),
    report_repo=Depends(get_report_repository),
):
    return RecalculateMetricsUseCase(insight_repo, report_repo)


async def get_get_active_risks_use_case(
    report_repo=Depends(get_report_repository),
    diagnosis_repo=Depends(get_diagnosis_repository),
):
    return GetActiveRisksUseCase(report_repo, diagnosis_repo)
