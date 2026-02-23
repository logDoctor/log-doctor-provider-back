from abc import ABC, abstractmethod

import msal
import structlog

from app.core import settings
from app.core.exceptions import UnauthorizedException

logger = structlog.get_logger()


class TokenProvider(ABC):
    """토큰 발급자 추상 머신"""

    @abstractmethod
    async def get_obo_token(self, sso_token: str) -> str:
        """SSO 토큰을 On-Behalf-Of 액세스 토큰으로 교환합니다."""
        pass


class EntraIDTokenProvider(TokenProvider):
    """Azure Entra ID를 사용한 토큰 발급 구현체"""

    async def get_obo_token(self, sso_token: str) -> str:
        authority = (
            f"https://login.microsoftonline.com/{settings.TENANT_ID or 'common'}"
        )

        client_credential = None
        if settings.AUTH_METHOD == "secret":
            client_credential = settings.CLIENT_SECRET

        app = msal.ConfidentialClientApplication(
            settings.CLIENT_ID,
            authority=authority,
            client_credential=client_credential,
        )

        scopes = ["https://management.azure.com/user_impersonation"]
        sso_token = sso_token.replace("Bearer ", "").strip()

        try:
            result = app.acquire_token_on_behalf_of(
                user_assertion=sso_token, scopes=scopes
            )
        except Exception:
            raise UnauthorizedException(
                "Failed to acquire OBO token due to an internal MSAL error."
            ) from None

        if "access_token" in result:
            return result["access_token"]

        error_desc = result.get("error_description", "Authentication failed")
        raise UnauthorizedException(f"OBO Token Exchange Failed: {error_desc}")
