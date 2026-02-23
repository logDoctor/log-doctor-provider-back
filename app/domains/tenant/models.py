from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class Tenant:
    id: str
    tenant_id: str
    is_active: bool
    created_at: str

    @staticmethod
    def create(tenant_id: str) -> "Tenant":
        """최초 테넌트 도메인 객체를 생성하는 팩토리 메서드입니다."""
        return Tenant(
            id=tenant_id,
            tenant_id=tenant_id,
            is_active=False,
            created_at=datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def from_dict(data: dict) -> "Tenant":
        """Cosmos DB 데이터로부터 테넌트 도메인 객체를 복원합니다."""
        return Tenant(
            id=data["id"],
            tenant_id=data["tenant_id"],
            is_active=data.get("is_active", False),
            created_at=data["created_at"],
        )

    def to_dict(self) -> dict:
        """Cosmos DB 저장을 위한 사전 형태로 변환합니다."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }
