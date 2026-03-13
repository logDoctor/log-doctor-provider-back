import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class NotificationType(Enum):
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    SYSTEM_ALERT = "SYSTEM_ALERT"


class NotificationStatus(Enum):
    SENT = "SENT"
    FAILED = "FAILED"


@dataclass
class Notification:
    notification_id: str
    tenant_id: str
    type: NotificationType
    summary: str
    recipient_count: int
    status: NotificationStatus
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        tenant_id: str,
        type: NotificationType,
        summary: str,
        recipient_count: int,
        status: NotificationStatus = NotificationStatus.SENT,
    ) -> "Notification":
        return cls(
            notification_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            type=type,
            summary=summary,
            recipient_count=recipient_count,
            status=status,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.notification_id,
            "tenant_id": self.tenant_id,
            "type": self.type.value,
            "summary": self.summary,
            "recipient_count": self.recipient_count,
            "status": self.status.value,
            "sent_at": self.sent_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Notification":
        return cls(
            notification_id=data["id"],
            tenant_id=data["tenant_id"],
            type=NotificationType(data["type"]),
            summary=data["summary"],
            recipient_count=data["recipient_count"],
            status=NotificationStatus(data["status"]),
            sent_at=datetime.fromisoformat(data["sent_at"]),
        )
