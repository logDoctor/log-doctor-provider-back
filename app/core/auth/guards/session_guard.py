from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# FastAPI 보안 인증 스키마
security = HTTPBearer(auto_error=False)


async def get_sso_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Authorization 헤더에서 토큰을 추출합니다."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication header is missing.",
        )
    return credentials.credentials
