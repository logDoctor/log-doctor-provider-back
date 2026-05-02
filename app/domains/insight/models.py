from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .constants import PeriodType


@dataclass
class InsightTrendItem:
    label: str
    detected: int
    resolved: int


@dataclass
class InsightEngineItem:
    engine_code: str
    count: int


@dataclass
class InsightDocument:
    id: str
    tenant_id: str
    agent_id: str
    period_type: PeriodType
    period_key: str
    total_reports: int = 0
    total_detected: int = 0
    total_resolved: int = 0
    total_healthy: int = 0
    active_risks_count: int = 0
    trend: List[InsightTrendItem] = field(default_factory=list)
    engine_distribution: List[InsightEngineItem] = field(default_factory=list)
    latest_report_id: Optional[str] = None
    last_updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    _etag: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "period_type": self.period_type,
            "period_key": self.period_key,
            "total_reports": self.total_reports,
            "total_detected": self.total_detected,
            "total_resolved": self.total_resolved,
            "total_healthy": self.total_healthy,
            "active_risks_count": self.active_risks_count,
            "trend": [
                {"label": t.label, "detected": t.detected, "resolved": t.resolved}
                for t in self.trend
            ],
            "engine_distribution": [
                {"engine_code": e.engine_code, "count": e.count}
                for e in self.engine_distribution
            ],
            "latest_report_id": self.latest_report_id,
            "last_updated_at": self.last_updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InsightDocument":
        return cls(
            id=data["id"],
            tenant_id=data["tenant_id"],
            agent_id=data["agent_id"],
            period_type=PeriodType(data["period_type"]),
            period_key=data["period_key"],
            total_reports=data.get("total_reports", 0),
            total_detected=data.get("total_detected", 0),
            total_resolved=data.get("total_resolved", 0),
            total_healthy=data.get("total_healthy", 0),
            active_risks_count=data.get("active_risks_count", 0),
            trend=[InsightTrendItem(**t) for t in data.get("trend", [])],
            engine_distribution=[
                InsightEngineItem(**e) for e in data.get("engine_distribution", [])
            ],
            latest_report_id=data.get("latest_report_id"),
            last_updated_at=data.get("last_updated_at", datetime.utcnow().isoformat()),
            _etag=data.get("_etag"),
        )
