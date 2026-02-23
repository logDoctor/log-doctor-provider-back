from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

F = TypeVar("F", bound=Callable[..., Any])

# FastAPI 보안 인증 스키마
security = HTTPBearer(auto_error=False)


async def get_sso_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Authorization 헤더에서 토큰을 추출합니다."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 헤더가 누락되었습니다.",
        )
    return credentials.credentials


def token_required(func: F) -> F:
    """
    유효한 SSO 토큰이 필요한 경우 사용하는 데코레이터입니다.

    Example:
        @router.get("/protected")
        @token_required
        async def protected_route():
            ...
    """

    @wraps(func)
    async def wrapper(
        *args: Any, _token: str = Depends(get_sso_token), **kwargs: Any
    ) -> Any:
        # get_sso_token이 401을 호출하지 않으면 통과
        return await func(*args, **kwargs)

    return wrapper  # type: ignore
