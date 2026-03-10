from enum import Enum

from pydantic import BaseModel


class IdentityType(str, Enum):
    """신원 유형 정의"""

    PLATFORM_ADMIN = "PLATFORM_ADMIN"  # 플랫폼 운영사 관리자
    TENANT_ADMIN = "TENANT_ADMIN"  # 테넌트(고객사) 관리자
    USER = "USER"  # 일반 사용자
    CLIENT_AGENT = "CLIENT_AGENT"  # 에이전트 계정
    CI_CD = "CI_CD"  # 자동화 계정
    UNKNOWN = "UNKNOWN"


class Identity(BaseModel):
    """시스템 내 사용자나 기계의 신원 정보를 담는 모델"""

    type: IdentityType
    id: str | None = None  # Entra ID Object ID (oid)
    name: str | None = None
    email: str | None = None
    roles: list[str] = []
    tenant_id: str | None = None
    sso_token: str | None = None

    def is_platform_admin(self) -> bool:
        """플랫폼 전체 운영 권한이 있는지 확인합니다."""
        return self.type == IdentityType.PLATFORM_ADMIN

    def is_tenant_admin(self) -> bool:
        """테넌트 관리자 권한이 있는지 확인합니다."""
        return self.type == IdentityType.TENANT_ADMIN

    def is_admin(self) -> bool:
        """관리 권한(플랫폼 또는 테넌트 관리자)이 있는지 확인합니다."""
        return self.is_platform_admin() or self.is_tenant_admin()

    def can_access_tenant(self, tenant_id: str) -> bool:
        """특정 테넌트 데이터에 접근 가능한지 확인합니다."""
        if self.is_platform_admin():
            return True
        return self.tenant_id == tenant_id
