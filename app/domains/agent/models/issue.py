import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

@dataclass
class AgentIssue:
    id: str
    tenant_id: str
    agent_id: str
    issue_type: str
    message: str
    raw_data: str | None
    created_at: str

    @staticmethod
    def create(tenant_id: str, agent_id: str, issue_type: str, message: str, raw_data: str | None = None) -> "AgentIssue":
        now = datetime.now(UTC).isoformat()
        return AgentIssue(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            agent_id=agent_id,
            issue_type=issue_type,
            message=message,
            raw_data=raw_data,
            created_at=now
        )

    @staticmethod
    def from_dict(data: dict) -> "AgentIssue":
        return AgentIssue(
            id=data["id"],
            tenant_id=data["tenant_id"],
            agent_id=data["agent_id"],
            issue_type=data["issue_type"],
            message=data.get("message", ""),
            raw_data=data.get("raw_data"),
            created_at=data["created_at"]
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "issue_type": self.issue_type,
            "message": self.message,
            "raw_data": self.raw_data,
            "created_at": self.created_at,
            "type": "issue" # CosmosDB 구분자
        }
