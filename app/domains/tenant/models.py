from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class TeamsInfo:
    team_id: str | None = None
    channel_id: str | None = None
    service_url: str | None = None

    @staticmethod
    def from_dict(data: dict | None) -> "TeamsInfo | None":
        if not data:
            return None
        return TeamsInfo(
            team_id=data.get("team_id"),
            channel_id=data.get("channel_id"),
            service_url=data.get("service_url"),
        )

    def to_dict(self) -> dict:
        return {
            "team_id": self.team_id,
            "channel_id": self.channel_id,
            "service_url": self.service_url,
        }


@dataclass
class Tenant:
    id: str
    tenant_id: str
    created_at: str
    registered_at: str | None = None  # 실제 사용자 등록 시점
    privileged_accounts: list[dict[str, str]] = field(
        default_factory=list
    )  # [{"email": "...", "user_id": "..."}]
    teams_info: TeamsInfo | None = None

    @staticmethod
    def register(tenant_id: str) -> "Tenant":
        """최초 테넌트 도메인 객체를 생성하는 팩토리 메서드입니다."""
        now = datetime.now(UTC).isoformat()
        return Tenant(
            id=tenant_id,
            tenant_id=tenant_id,
            created_at=now,
            registered_at=now,
            privileged_accounts=[],
            teams_info=None,
        )

    @staticmethod
    def from_dict(data: dict) -> "Tenant":
        """Cosmos DB 데이터로부터 테넌트 도메인 객체를 복원합니다."""
        return Tenant(
            id=data["id"],
            tenant_id=data["tenant_id"],
            created_at=data["created_at"],
            registered_at=data.get("registered_at"),
            privileged_accounts=data.get("privileged_accounts", []),
            teams_info=TeamsInfo.from_dict(data.get("teams_info")),
        )

    def to_dict(self) -> dict:
        """Cosmos DB 저장을 위한 사전 형태로 변환합니다."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at,
            "registered_at": self.registered_at,
            "privileged_accounts": self.privileged_accounts or [],
            "teams_info": self.teams_info.to_dict() if self.teams_info else None,
        }

    def add_privileged_account(self, email: str, user_id: str) -> None:
        # 이메일 기준으로 중복 체크 및 업데이트
        for account in self.privileged_accounts:
            if account["email"] == email:
                account["user_id"] = user_id
                return

        self.privileged_accounts.append({"email": email, "user_id": user_id})

    def remove_privileged_account(self, email: str) -> None:
        self.privileged_accounts = [
            a for a in self.privileged_accounts if a["email"] != email
        ]

    def is_registered(self) -> bool:
        return self.registered_at is not None
