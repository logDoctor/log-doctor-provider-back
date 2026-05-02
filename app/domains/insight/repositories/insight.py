from abc import ABC, abstractmethod
from typing import List, Optional

from ..models import InsightDocument, PeriodType


class InsightRepository(ABC):
    @abstractmethod
    async def get_by_id(
        self, tenant_id: str, agent_id: str, period_type: PeriodType, period_key: str
    ) -> Optional[InsightDocument]:
        pass

    @abstractmethod
    async def upsert(self, insight: InsightDocument) -> None:
        pass

    @abstractmethod
    async def get_latest_daily_items(
        self, tenant_id: str, agent_id: str, limit: int
    ) -> List[InsightDocument]:
        pass
