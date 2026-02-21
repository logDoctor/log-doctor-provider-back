from fastapi_azure_auth import MultiTenantAzureAuthorizationCodeBearer

from app.core.auth_provider import get_token_provider
from app.core.config import settings

# Teams SSO 토큰은 종종 Client ID만을 Audience(aud)로 사용하거나, 설정된 App ID URI를 사용합니다.
expected_audience = settings.APP_ID_URI or settings.CLIENT_ID

# Azure AD JWT Token Validation Scheme (Multi-tenant)
azure_scheme = MultiTenantAzureAuthorizationCodeBearer(
    app_client_id=[settings.CLIENT_ID, expected_audience],
    scopes={
        f"api://{settings.CLIENT_ID}/access_as_user": "Access Log Doctor API as user",
    },
    validate_iss=False,
)


async def get_obo_access_token(sso_token: str) -> str:
    """
    설정된 Auth Provider를 통해 프론트엔드의 SSO 토큰을 액세스 토큰으로 교환합니다.
    주의: MFA 요구사항 등으로 인해 로컬 환경에서 실패할 가능성이 높습니다.
    """
    provider = get_token_provider()
    return await provider.get_obo_token(sso_token)


async def get_service_access_token() -> str:
    """
    설정된 Auth Provider를 통해 서비스 자체의 권한(Identity)으로 액세스 토큰을 가져옵니다. (직방)
    """
    provider = get_token_provider()
    return await provider.get_service_token()
