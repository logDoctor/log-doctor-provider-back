from enum import Enum

from pydantic import BaseModel


class IdentityType(str, Enum):
    """신원 유형 정의"""

    ADMIN = "ADMIN"
    CLIENT_AGENT = "CLIENT_AGENT"
    CI_CD = "CI_CD"
    UNKNOWN = "UNKNOWN"


class Identity(BaseModel):
    """시스템 내 사용자나 기계의 신원 정보를 담는 모델"""

    type: IdentityType
    id: str | None = None
    name: str | None = None
    roles: list[str] = []
    tenant_id: str | None = None
