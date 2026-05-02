from typing import Dict, List, Optional

from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.cosmos.aio import CosmosClient

from app.core.logging import get_logger
from app.domains.insight.constants import PERIOD_CONTAINER_MAP
from app.domains.insight.models import InsightDocument, PeriodType
from app.domains.insight.repositories.insight import InsightRepository

logger = get_logger("azure_insight_repository")


class AzureInsightRepository(InsightRepository):
    def __init__(self, client: CosmosClient, database_name: str):
        self.client = client
        self.db = client.get_database_client(database_name)

    def _get_container(self, period_type: PeriodType):
        container_name = PERIOD_CONTAINER_MAP[period_type]
        return self.db.get_container_client(container_name)

    async def get_by_id(
        self, tenant_id: str, agent_id: str, period_type: PeriodType, period_key: str
    ) -> Optional[InsightDocument]:
        container = self._get_container(period_type)
        doc_id = (
            f"{agent_id}:{period_key}" if period_type != PeriodType.TOTAL else agent_id
        )

        try:
            data = await container.read_item(item=doc_id, partition_key=tenant_id)
            return InsightDocument.from_dict(data)
        except ResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(
                "failed_to_get_insight",
                agent_id=agent_id,
                period=period_type,
                error=str(e),
            )
            return None

    async def upsert(self, insight: InsightDocument) -> None:
        container = self._get_container(insight.period_type)
        data = insight.to_dict()

        try:
            if insight._etag:
                # 낙관적 잠금 적용
                await container.upsert_item(
                    data, etag=insight._etag, match_condition=True
                )
            else:
                await container.upsert_item(data)
        except Exception as e:
            logger.error(
                "failed_to_upsert_insight",
                agent_id=insight.agent_id,
                period=insight.period_type,
                error=str(e),
            )
            raise

    async def get_latest_daily_items(
        self, tenant_id: str, agent_id: str, limit: int
    ) -> List[InsightDocument]:
        """롤링 윈도우 집계를 위해 최근 N일치의 데이터를 가져옵니다."""
        container = self._get_container(PeriodType.DAILY)
        query = (
            "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.agent_id = @agent_id "
            "ORDER BY c.period_key DESC OFFSET 0 LIMIT @limit"
        )
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@agent_id", "value": agent_id},
            {"name": "@limit", "value": limit},
        ]

        try:
            items = []
            async for item in container.query_items(
                query=query, parameters=parameters, enable_cross_partition_query=False
            ):
                items.append(InsightDocument.from_dict(item))
            return items
        except Exception as e:
            logger.error(
                "failed_to_query_latest_daily_insights", agent_id=agent_id, error=str(e)
            )
            return []
