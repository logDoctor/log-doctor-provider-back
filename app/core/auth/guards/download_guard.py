import jwt
from fastapi import Depends, HTTPException, Request, status

from app.core.config import settings


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
