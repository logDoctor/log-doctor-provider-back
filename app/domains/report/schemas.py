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


class DiagnosisSchema(BaseModel):
    """개별 진단 항목 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    report_id: str
    tenant_id: str
    rule_id: str
    status: str  # DETECTED | HEALTHY
    description: str
    resource_id: str
    remediation: str
    created_at: str | None = None


class AddDiagnosesRequest(BaseModel):
    """진단 항목 일괄 추가 요청"""

    items: list[DiagnosisSchema]


class ReportUpdateSchema(BaseModel):
    """리포트 정보 업데이트 스키마 (PATCH 용)"""

    status: ReportStatus | None = None
    error: str | None = None
