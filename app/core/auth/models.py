from enum import Enum

from pydantic import BaseModel


class IdentityType(str, Enum):
    """신원 유형 정의"""

    GLOBAL_ADMIN = "GLOBAL_ADMIN"  # 전역 관리자 (Global Admin)
    APP_ADMIN = "APP_ADMIN"  # 앱 관리자 (App Admin)
    CLIENT_AGENT = "CLIENT_AGENT"
    CI_CD = "CI_CD"
    UNKNOWN = "UNKNOWN"


class Identity(BaseModel):
    """시스템 내 사용자나 기계의 신원 정보를 담는 모델"""

    type: IdentityType
    id: str | None = None  # Entra ID Object ID (oid)
    name: str | None = None
    email: str | None = None
    roles: list[str] = []
    is_global_admin: bool = False  # 전역 관리자 여부
    is_app_admin: bool = False  # 앱 관리자 여부
    tenant_id: str | None = None
    sso_token: str | None = None
