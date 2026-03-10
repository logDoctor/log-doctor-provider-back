import structlog
from fastapi import Depends, Request

from app.core.exceptions import UnauthorizedException

from ..dependencies import get_identity_extractor
from ..models import Identity, IdentityType


def get_current_identity(
    request: Request,
    identity_extractor=Depends(get_identity_extractor),
) -> Identity:
    """헤더 정보를 바탕으로 호출자의 신원을 확인합니다."""
    identity = identity_extractor.extract(request.headers.get("Authorization"))

    if identity.type == IdentityType.UNKNOWN:
        raise UnauthorizedException(
            "AUTH_REQUIRED|Invalid or missing authentication information."
        )

    # 로그에 사용자 컨텍스트를 자동으로 바인딩 (structlog contextvars 활용)
    structlog.contextvars.bind_contextvars(
        tenant_id=identity.tenant_id,
        user_id=identity.id,
        user_email=identity.email,
        identity_type=identity.type.value,
    )

    return identity
