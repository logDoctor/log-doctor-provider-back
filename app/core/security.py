from app.core.auth_provider import get_token_provider


async def get_obo_access_token(sso_token: str) -> str:
    """
    설정된 Auth Provider를 통해 프론트엔드의 SSO 토큰을 액세스 토큰으로 교환합니다.
    이 로직은 클라우드에 독립적이며 TokenProvider 인터페이스에 의존합니다.
    """
    provider = get_token_provider()
    return await provider.get_obo_token(sso_token)
