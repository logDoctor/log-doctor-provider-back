from pydantic import BaseModel, ConfigDict

from app.domains.agent.models import AnalysisLevel

from .models import ReportStatus


class ReportSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str
    trace_id: str
    status: ReportStatus
    triggered_by: str
    level: AnalysisLevel
    request_params: dict | None = None
    result: dict | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class CreateReportRequest(BaseModel):
    agent_id: str
    level: AnalysisLevel = AnalysisLevel.L1
    start_time: str | None = None
    end_time: str | None = None


class CreateReportResponse(BaseModel):
    message: str
    report: ReportSchema
