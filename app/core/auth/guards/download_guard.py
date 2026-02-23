from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

import jwt
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings

F = TypeVar("F", bound=Callable[..., Any])


async def check_download_token(request: Request, token: str | None = None) -> bool:
    """다운로드 토큰을 강제하는 의존성 주입 함수입니다. (Internal dependency)"""
    # 1. 1차 방어: User-Agent 필터링 (일반 웹 브라우저 차단)
    user_agent = request.headers.get("user-agent", "").lower()
    blocked_agents = ["mozilla", "chrome", "safari", "edge", "applewebkit"]

    if any(agent in user_agent for agent in blocked_agents):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Direct browser downloads are not allowed for this endpoint.",
        )

    # 2. 2차 방어: JWT 토큰 검증
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Download token is required",
        )

    try:
        jwt.decode(token, settings.DOWNLOAD_SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid download token"
        ) from None

    return True


def download_token_required[F: Callable[..., Any]](func: F) -> F:
    """
    고객사 에이전트 패키지 다운로드 기능을 보호하는 데코레이터입니다.
    User-Agent 확인 및 무기한 JWT 토큰 검증을 수행합니다.

    Example:
        @router.get("/download")
        @download_token_required
        async def download_package(self, version: str = "latest"):
            ...
    """

    @wraps(func)
    async def wrapper(
        *args: Any, _verified: bool = Depends(check_download_token), **kwargs: Any
    ) -> Any:
        # 이 데코레이터가 붙은 라우터 함수는 시그니처 매칭에 의해
        # _verified 파라미터가 자동으로 주입 및 실행됩니다.
        # kwargs에서 _verified를 제거하여 원본 함수에 전달되지 않게 합니다.
        kwargs.pop("_verified", None)
        return await func(*args, **kwargs)

    return wrapper  # type: ignore
