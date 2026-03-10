import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from app.domains.agent.models import AnalysisLevel


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
    level: AnalysisLevel
    request_params: dict | None = None  # 분석 요청 시 입력된 파라미터 컨텍스트
    result: dict | None = None  # 분석 완료 후 생성된 결과 데이터
    error: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def create(
        tenant_id: str,
        agent_id: str,
        trace_id: str,
        triggered_by: str,
        level: AnalysisLevel,
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
            level=level,
            request_params=request_params,
            created_at=now,
            updated_at=now,
        )

    def mark_as_failed(self, error_message: str):
        """리포트 분석 요청 실패를 기록합니다."""
        self.status = ReportStatus.FAILED
        self.error = error_message
        self.updated_at = datetime.now(UTC).isoformat()

    @staticmethod
    def from_dict(data: dict) -> "Report":
        return Report(
            id=data["id"],
            tenant_id=data["tenant_id"],
            agent_id=data["agent_id"],
            trace_id=data["trace_id"],
            status=ReportStatus(data["status"]),
            triggered_by=data.get("triggered_by", "system"),
            level=AnalysisLevel(data.get("level", AnalysisLevel.L1)),
            request_params=data.get("request_params"),
            result=data.get("result"),
            error=data.get("error"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "trace_id": self.trace_id,
            "status": self.status.value,
            "triggered_by": self.triggered_by,
            "level": self.level.value if hasattr(self.level, "value") else self.level,
            "request_params": self.request_params,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
