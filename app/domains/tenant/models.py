from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Tenant:
    id: str
    tenant_id: str
    created_at: str
    registered_at: str | None = None  # 실제 사용자 등록 시점
    privileged_accounts: list[dict[str, str]] = field(
        default_factory=list
    )  # [{"email": "...", "user_id": "..."}]

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
        )

    def to_dict(self) -> dict:
        """Cosmos DB 저장을 위한 사전 형태로 변환합니다."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at,
            "registered_at": self.registered_at,
            "privileged_accounts": self.privileged_accounts or [],
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
