from app.core.config import settings


class AzureDirectoryRole:
    """Azure AD에서 사전에 정의된 고유 ID(UUID들)"""

    GLOBAL_ADMIN = "62e90394-69f5-4237-9190-012177145e10"
    PRIVILEGED_ROLE_ADMIN = "e8611eb8-c13f-4745-8462-24867d9a65ed"
    APPLICATION_ADMIN = "9b89c20d-ad03-4503-ad20-039103212108"
    CLOUD_APPLICATION_ADMIN = "158c15cc-0570-44c1-848e-0f04dc22312b"

    # 조직 전체 동의(Admin Consent)가 가능한 강력한 관리자 역할들
    ADMIN_CONSENT_CAPABLE_ROLES = [
        GLOBAL_ADMIN,
        PRIVILEGED_ROLE_ADMIN,
        APPLICATION_ADMIN,
        CLOUD_APPLICATION_ADMIN,
    ]

class AppRoleName:
    """우리 앱(LogDoctor)의 manifest.json에 정의된 전용 역할명 및 고유 ID(UUID)"""

    # 역할명 (토큰의 roles 클레임에 포함되는 문자열)
    PLATFORM_ADMIN = "PlatformAdmin"
    TENANT_ADMIN = "TenantAdmin"
    PRIVILEGED_USER = "PrivilegedUser"

    # 실제 Azure Portal에 등록된 앱 역할 ID (환경별 .env에서 로드)
    @property
    def TENANT_ADMIN_ID(self) -> str:
        return settings.TENANT_ADMIN_ROLE_ID

    @property
    def PRIVILEGED_USER_ID(self) -> str:
        return settings.PRIVILEGED_USER_ROLE_ID

    @property
    def PLATFORM_ADMIN_ID(self) -> str:
        return settings.PLATFORM_ADMIN_ROLE_ID


# 기존 코드 호환성을 위해 인스턴스로 제공
AppRoleName = AppRoleName()


class TokenClaim:
    """JWT 토큰 내의 표준 및 커스텀 클레임 키 명칭"""

    WIDS = "wids"
    ROLES = "roles"
    TID = "tid"
    GROUPS = "groups"
    TENANT_ID = "tenant_id"
    TENANTID = "tenantid"
    MICROSOFT_TENANT_SCHEMA = "http://schemas.microsoft.com/identity/claims/tenantid"

    OID = "oid"
    SUB = "sub"
    NAME = "name"
    UPN = "upn"
    PREFERRED_USERNAME = "preferred_username"
    APPID = "appid"
    AZP = "azp"
    IDTYP = "idtyp"
