from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import Depends, HTTPException, status

from ..dependencies import get_admin_verifier
from ..models import Identity
from ..services.admin_verifier import AuthError
from .identity_guard import get_current_identity

F = TypeVar("F", bound=Callable[..., Any])


async def check_admin(
    identity: Identity = Depends(get_current_identity),
    verifier=Depends(get_admin_verifier),
) -> Identity:
    """관리자 권한을 강제하는 의존성 주입 함수입니다. (Internal dependency)"""
    try:
        return verifier.verify(identity)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


def admin_required(func: F) -> F:
    """
    관리자 권한을 강제하는 데코레이터입니다.

    Example:
        @router.post("/items")
        @admin_required
        async def create_item(item: Item):
            ...
    """

    @wraps(func)
    async def wrapper(
        *args: Any, _identity: Identity = Depends(check_admin), **kwargs: Any
    ) -> Any:
        return await func(*args, **kwargs)

    return wrapper  # type: ignore
