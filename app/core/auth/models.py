from enum import Enum

from pydantic import BaseModel

from .constants import AzureDirectoryRole


class IdentityType(str, Enum):
    """신원 유형 정의"""

    PLATFORM_ADMIN = "PLATFORM_ADMIN"  # 플랫폼 운영사 관리자
    TENANT_ADMIN = "TENANT_ADMIN"  # 테넌트(고객사) 관리자
    PRIVILEGED_USER = "PRIVILEGED_USER"  # 위임된 운영자
    USER = "USER"  # 일반 사용자
    CI_CD = "CI_CD"  # 자동화(CI/CD) 기계 신원
    UNKNOWN = "UNKNOWN"


class Identity(BaseModel):
    """시스템 내 사용자나 기계의 신원 정보를 담는 모델"""

    type: IdentityType
    id: str | None = None  # Entra ID Object ID (oid)
    name: str | None = None
    email: str | None = None
    roles: list[str] = []
    wids: list[str] = []  # Azure AD 수준의 디렉터리 역할 ID 목록
    groups: list[str] = []  # 사용자 그룹 ID 목록 (디렉터리 역할 포함 가능)
    tenant_id: str | None = None
    sso_token: str | None = None

    def is_platform_admin(self) -> bool:
        """플랫폼 전체 운영 권한이 있는지 확인합니다."""
        return self.type == IdentityType.PLATFORM_ADMIN

    def is_tenant_admin(self) -> bool:
        """테넌트 관리자 권한이 있는지 확인합니다."""
        return self.type == IdentityType.TENANT_ADMIN

    def is_privileged_user(self) -> bool:
        """위임된 운영자(PrivilegedUser) 권한이 있는지 확인합니다."""
        return self.type == IdentityType.PRIVILEGED_USER

    def is_ci_cd(self) -> bool:
        """자동화(CI/CD) 기계 신원이 있는지 확인합니다."""
        return self.type == IdentityType.CI_CD

    def is_directory_admin(self) -> bool:
        """Azure 디렉터리 수준의 관리자(Global Admin 등)인지 확인합니다."""
        # wids와 groups를 합쳐서 관리자 역할 ID가 있는지 확인합니다.
        combined_indicators = set(self.wids) | set(self.groups)
        return any(
            rid in AzureDirectoryRole.ADMIN_CONSENT_CAPABLE_ROLES
            for rid in combined_indicators
        )

    def is_privileged(self) -> bool:
        """이용 권한(플랫폼/테넌트 관리자, 위임된 운영자 또는 디렉터리 관리자)이 있는지 확인합니다."""
        return (
            self.is_platform_admin()
            or self.is_tenant_admin()
            or self.is_privileged_user()
            or self.is_ci_cd()
        )

    def can_access_tenant(self, tenant_id: str) -> bool:
        """특정 테넌트 데이터에 접근 가능한지 확인합니다."""
        if self.is_platform_admin():
            return True
        return self.tenant_id == tenant_id
