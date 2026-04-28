import uuid
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class Schedule:
    """정기 검진 스케줄 엔티티 — Agent aggregate의 하위 개념"""

    id: str
    tenant_id: str       # Cosmos partition key
    agent_id: str
    enabled: bool
    cron_expression: str  # 5-field: "0 9 * * 1"
    timezone: str         # IANA: "Asia/Seoul"
    language: str         # "ko" | "en"
    configurations: list[dict]  # DiagnosticRuleConfiguration 스냅샷 (생성 시 검증)
    last_run_at: str | None
    next_run_at: str | None
    created_at: str
    updated_at: str
    created_by: str
    _etag: str | None = None  # 낙관적 잠금용

    @staticmethod
    def create(
        tenant_id: str,
        agent_id: str,
        enabled: bool,
        cron_expression: str,
        timezone: str,
        language: str,
        configurations: list[dict],
        next_run_at: str | None,
        created_by: str,
    ) -> "Schedule":
        now = datetime.now(UTC).isoformat()
        return Schedule(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            agent_id=agent_id,
            enabled=enabled,
            cron_expression=cron_expression,
            timezone=timezone,
            language=language,
            configurations=configurations,
            last_run_at=None,
            next_run_at=next_run_at,
            created_at=now,
            updated_at=now,
            created_by=created_by,
        )

    def update_last_run_at(self, run_time: datetime) -> None:
        self.last_run_at = run_time.isoformat()
        self.updated_at = datetime.now(UTC).isoformat()

    def update_next_run_at(self, next_time: datetime) -> None:
        self.next_run_at = next_time.isoformat()
        self.updated_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "enabled": self.enabled,
            "cron_expression": self.cron_expression,
            "timezone": self.timezone,
            "language": self.language,
            "configurations": self.configurations,
            "last_run_at": self.last_run_at,
            "next_run_at": self.next_run_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by,
        }

    @staticmethod
    def from_dict(data: dict) -> "Schedule":
        s = Schedule(
            id=data["id"],
            tenant_id=data["tenant_id"],
            agent_id=data["agent_id"],
            enabled=data.get("enabled", True),
            cron_expression=data["cron_expression"],
            timezone=data.get("timezone", "UTC"),
            language=data.get("language", "ko"),
            configurations=data.get("configurations", []),
            last_run_at=data.get("last_run_at"),
            next_run_at=data.get("next_run_at"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            created_by=data.get("created_by", ""),
        )
        s._etag = data.get("_etag")
        return s
