import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class ReportStatus(str, Enum):
    """리포트 분석 상태"""

    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class Report:
    """분석 리포트 엔티티 (상태 기반 관리)"""

    id: str
    tenant_id: str
    agent_id: str
    trace_id: str
    status: ReportStatus
    triggered_by: str
    is_initial: bool = False
    request_params: dict | None = None  # 분석 요청 시 입력된 파라미터 컨텍스트

    summary: dict | None = None  # 분석 완료 및 요약 통계 데이터
    error: str | None = None
    created_at: str = ""
    updated_at: str = ""
    _etag: str | None = None  # 낙관적 락(OCC)용 ETag

    @property
    def is_analyzing(self) -> bool:
        """리포트가 현재 분석 중(진행 중)인지 확인합니다."""
        return self.status == ReportStatus.ANALYZING

    @staticmethod
    def create(
        tenant_id: str,
        agent_id: str,
        trace_id: str,
        triggered_by: str,
        is_initial: bool = False,
        request_params: dict | None = None,
    ) -> "Report":

        now = datetime.now(UTC).isoformat()
        return Report(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            agent_id=agent_id,
            trace_id=trace_id,
            status=ReportStatus.ANALYZING,
            triggered_by=triggered_by,
            is_initial=is_initial,
            request_params=request_params,
            created_at=now,
            updated_at=now,
        )

    def mark_as_failed(self, error_message: str):
        """리포트 분석 요청 실패를 기록합니다."""
        self.status = ReportStatus.FAILED
        self.error = error_message
        self.updated_at = datetime.now(UTC).isoformat()

    def complete_analysis(self, summary: dict, error: str | None = None):
        """분석 완료 결과를 리포트에 반영합니다."""
        if error:
            self.status = ReportStatus.FAILED
            self.error = error
        else:
            self.status = ReportStatus.COMPLETED
            self.summary = summary

        self.updated_at = datetime.now(UTC).isoformat()

    def update(
        self,
        status: ReportStatus | None = None,
        error: str | None = None,
        summary: dict | None = None,
    ) -> list[str]:
        """리포트 정보를 부분 업데이트하고 변경된 필드 목록을 반환합니다."""
        updated_fields = []
        if status and self.status != status:
            self.status = status
            updated_fields.append("status")
        if error is not None and self.error != error:
            self.error = error
            updated_fields.append("error")
        if summary is not None:
            if self.summary is None or not isinstance(self.summary, dict):
                self.summary = {}
            changed = False
            for k, v in summary.items():
                if self.summary.get(k) != v:
                    self.summary[k] = v
                    changed = True
            if changed:
                updated_fields.append("summary")

        if updated_fields:
            self.updated_at = datetime.now(UTC).isoformat()

        return updated_fields

    @staticmethod
    def from_dict(data: dict) -> "Report":
        return Report(
            id=data["id"],
            tenant_id=data["tenant_id"],
            agent_id=data["agent_id"],
            trace_id=data["trace_id"],
            status=ReportStatus(data["status"]),
            triggered_by=data.get("triggered_by", "system"),
            is_initial=data.get("is_initial", False),
            request_params=data.get("request_params"),
            summary=data.get("summary"),
            error=data.get("error"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            _etag=data.get("_etag"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "trace_id": self.trace_id,
            "status": self.status.value,
            "triggered_by": self.triggered_by,
            "is_initial": self.is_initial,
            "request_params": self.request_params,
            "summary": self.summary,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Diagnosis:
    """개별 진단 항목 엔티티 (Atomic Finding)"""

    id: str
    report_id: str
    tenant_id: str
    inspection_code: str
    status: str  # DETECTED | HEALTHY | UNDIAGNOSED

    description: str
    resource_id: str
    prescriptions: list[str]
    resource_group: dict
    is_resolved: bool = False
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def create(
        report_id: str,
        tenant_id: str,
        inspection_code: str,
        status: str,
        description: str,
        resource_id: str,
        prescriptions: list[str],
        resource_group: str | None = None,
        is_resolved: bool = False,
    ) -> "Diagnosis":
        now = datetime.now(UTC).isoformat()
        return Diagnosis(
            id=str(uuid.uuid4()),
            report_id=report_id,
            tenant_id=tenant_id,
            inspection_code=inspection_code,
            status=status,
            description=description,
            resource_id=resource_id,
            prescriptions=prescriptions,
            resource_group=resource_group,
            is_resolved=is_resolved,
            created_at=now,
            updated_at=now,
        )

    @staticmethod
    def from_dict(data: dict) -> "Diagnosis":
        return Diagnosis(
            id=data["id"],
            report_id=data["report_id"],
            tenant_id=data["tenant_id"],
            inspection_code=data.get("inspection_code", data.get("rule_code")),
            status=data["status"],
            description=data["description"],
            resource_id=data["resource_id"],
            prescriptions=data.get("prescriptions", []),
            resource_group=data.get("resource_group"),
            is_resolved=data.get("is_resolved", False),
            created_at=data["created_at"],
            updated_at=data.get("updated_at", data["created_at"]),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "tenant_id": self.tenant_id,
            "inspection_code": self.inspection_code,
            "status": self.status,
            "description": self.description,
            "resource_id": self.resource_id,
            "prescriptions": self.prescriptions,
            "resource_group": self.resource_group,
            "is_resolved": self.is_resolved,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
