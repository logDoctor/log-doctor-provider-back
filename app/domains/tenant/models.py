from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Tenant:
    id: str
    tenant_id: str
    created_at: str
    registered_at: str | None = None  # 실제 사용자 등록 시점
    privileged_accounts: list[str] = field(default_factory=list)  # 운영자 권한을 가진 계정 리스트

    @staticmethod
    def register(tenant_id: str) -> "Tenant":
        """최초 테넌트 도메인 객체를 생성하는 팩토리 메서드입니다."""
        now = datetime.now(UTC).isoformat()
        return Tenant(
            id=tenant_id,
            tenant_id=tenant_id,
            created_at=now,
            registered_at=now,
            privileged_accounts=[]
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
    
    def add_privileged_account(self, email: str) -> None:
        if email not in self.privileged_accounts:
            self.privileged_accounts.append(email)

    def remove_privileged_account(self, email: str) -> None:
        if email in self.privileged_accounts:
            self.privileged_accounts.remove(email)
            
    def update_privileged_accounts(self, new_accounts: list[str], requester_email: str | None = None) -> None:
        """
        운영자 권한 계정 리스트를 도메인 규칙에 맞게 덮어씁니다(Replace).
        안전장치로써, 요청을 수행하는 관리자 본인의 이메일은 실수로 누락되더라도 강제로 포함시킵니다.
        """
        accounts = set(new_accounts)
        if requester_email:
            accounts.add(requester_email)
        self.privileged_accounts = list(accounts)
        
    def is_registered(self) -> bool:
        return self.registered_at is not None