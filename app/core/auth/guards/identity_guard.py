from collections.abc import Callable
from functools import wraps
from typing import Annotated, Any, TypeVar

from fastapi import Depends, Header, Request

from ..dependencies import get_identity_extractor
from ..models import Identity

F = TypeVar("F", bound=Callable[..., Any])


def get_current_identity(
    request: Request,
    extractor=Depends(get_identity_extractor),
    x_ms_client_principal: Annotated[
        str | None, Header(alias="X-MS-CLIENT-PRINCIPAL")
    ] = None,
) -> Identity:
    """헤더 정보를 바탕으로 호출자의 신원을 확인합니다."""
    auth_header = request.headers.get("Authorization")
    return extractor.extract(x_ms_client_principal, auth_header)


def identity_required(func: F) -> F:
    """
    호출자의 신원 정보가 필요한 경우 사용하는 데코레이터입니다.

    인자에 'identity'가 있을 경우 자동으로 추출된 Identity 객체를 주입합니다.

    Example:
        @router.get("/me")
        @identity_required
        async def get_me(identity: Identity):
            return identity
    """

    @wraps(func)
    async def wrapper(
        *args: Any, _identity: Identity = Depends(get_current_identity), **kwargs: Any
    ) -> Any:
        if "identity" in kwargs:
            kwargs["identity"] = _identity
        return await func(*args, **kwargs)

    return wrapper  # type: ignore
