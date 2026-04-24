from pydantic import BaseModel, ConfigDict

from .models import ReportStatus


class ResourceGroupItem(BaseModel):
    """리소스 그룹 식별자 스펙 (ID와 Name 동반)"""

    id: str
    name: str


class DiagnosisSchema(BaseModel):
    """개별 진단 항목 스키마"""

    model_config = ConfigDict(from_attributes=True)

    id: str | None = None
    report_id: str
    tenant_id: str
    inspection_code: str

    status: str  # DETECTED | HEALTHY
    description: str
    resource_id: str
    prescriptions: list[str]
    resource_group: ResourceGroupItem
    is_resolved: bool = False
    created_at: str | None = None
    updated_at: str | None = None


class ReportSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    agent_id: str
    trace_id: str
    status: ReportStatus
    triggered_by: str
    is_initial: bool
    request_params: dict | None = None

    summary: dict | None = None
    diagnoses: list[DiagnosisSchema] | None = None
    error: str | None = None
    created_at: str
    updated_at: str


class DiagnosticRuleConfiguration(BaseModel):
    """진단 규칙 실행 단위를 지정하는 스펙"""

    inspection_codes: list[str]
    resource_groups: list[ResourceGroupItem] | None = None


class CreateReportRequest(BaseModel):
    agent_id: str
    start_time: str | None = None
    end_time: str | None = None
    language: str | None = "ko"
    configurations: list[DiagnosticRuleConfiguration]


class CreateReportResponse(BaseModel):
    message: str
    report: ReportSchema


class AddDiagnosesRequest(BaseModel):
    """진단 항목 일괄 추가 요청"""

    items: list[DiagnosisSchema]


class ReportUpdateSchema(BaseModel):
    """리포트 정보 업데이트 스키마 (PATCH 용)"""

    tenant_id: str  # 명시적 전달 필수화
    status: ReportStatus | None = None
    error: str | None = None


class UpdateDiagnosisResolutionRequest(BaseModel):
    """진단 항목 해결 상태 업데이트 요청"""

    is_resolved: bool


class ReportListResponse(BaseModel):
    """리포트 목록 응답 스키마 (페이지네이션 지원)"""

    items: list[ReportSchema]
    next_cursor: str | None = None
