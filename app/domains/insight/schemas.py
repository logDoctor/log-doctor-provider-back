from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class InsightTrendItemSchema(BaseModel):
    label: str
    detected: int
    resolved: int


class InsightEngineItemSchema(BaseModel):
    engine_code: str
    label: str
    count: int


class InsightResponse(BaseModel):
    period: str
    period_label: str
    health_score: int
    active_risks_count: int
    total_reports: int
    total_detected: int
    total_resolved: int
    trend: List[InsightTrendItemSchema]
    engine_distribution: List[InsightEngineItemSchema]
    last_updated_at: str


class InsightEventMessage(BaseModel):
    event_type: str  # "report_completed" | "diagnosis_resolved"
    tenant_id: str
    agent_id: str
    report_id: str
    diagnosis_id: Optional[str] = None
    is_resolved: Optional[bool] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class InsightRebuildResponse(BaseModel):
    status: str
    agent_id: str
    containers_updated: List[str]
    total_reports_processed: int
