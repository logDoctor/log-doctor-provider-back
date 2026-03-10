from fastapi import Depends

from app.core.exceptions import ForbiddenException

from ..models import Identity
from .identity_guard import get_current_identity


async def admin_verify_guard(
    identity: Identity = Depends(get_current_identity),
) -> Identity:
    """관리자 권한을 강제하는 의존성 주입 함수입니다. (Internal dependency)"""
    if not identity.is_admin():
        raise ForbiddenException(detail="Administrator privileges are required.")

    return identity
