from fastapi import Depends, HTTPException, status

from ..dependencies import get_admin_verifier
from ..models import Identity
from ..services.admin_verifier import AuthError
from .identity_guard import get_current_identity


async def check_admin(
    identity: Identity = Depends(get_current_identity),
    verifier=Depends(get_admin_verifier),
) -> Identity:
    """관리자 권한을 강제하는 의존성 주입 함수입니다. (Internal dependency)"""
    try:
        return verifier.verify(identity)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e

