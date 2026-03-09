
from fastapi import Depends, Request

from app.core.exceptions import UnauthorizedException

from ..dependencies import get_identity_extractor
from ..models import Identity, IdentityType


def get_current_identity(
    request: Request,
    extractor=Depends(get_identity_extractor),
) -> Identity:
    """헤더 정보를 바탕으로 호출자의 신원을 확인합니다."""
    auth_header = request.headers.get("Authorization")
    identity = extractor.extract(auth_header)

    if identity.type == IdentityType.UNKNOWN:
        raise UnauthorizedException("AUTH_REQUIRED|유효하지 않은 인증 정보입니다.")

    return identity
