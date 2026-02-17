from abc import ABC, abstractmethod

import msal

from .config import settings


class TokenProvider(ABC):
    @abstractmethod
    async def get_obo_token(self, sso_token: str) -> str:
        """Exchange SSO token for an On-Behalf-Of access token."""
        pass


class EntraIDTokenProvider(TokenProvider):
    async def get_obo_token(self, sso_token: str) -> str:
        """SSO 토큰을 On-Behalf-Of 액세스 토큰으로 교환합니다."""
        authority = (
            f"https://login.microsoftonline.com/{settings.TENANT_ID or 'common'}"
        )

        # AUTH_METHOD에 따라 클라이언트 인증 정보 결정
        client_credential = None
        if settings.AUTH_METHOD == "secret":
            client_credential = settings.CLIENT_SECRET
        elif settings.AUTH_METHOD == "managed_identity":
            # 엄격한 Managed Identity OBO의 경우 MSAL은 client_assertion을 요구합니다.
            # 여기서는 확장이 가능한 단순화된 로직을 제공합니다.
            # (운영 환경에서는 Federated Credentials/Assertion을 사용해야 할 수 있습니다.)
            client_credential = None

        app = msal.ConfidentialClientApplication(
            settings.CLIENT_ID,
            authority=authority,
            client_credential=client_credential,
        )

        scopes = ["https://management.core.windows.net//user_impersonation"]

        result = app.acquire_token_on_behalf_of(user_assertion=sso_token, scopes=scopes)

        if "access_token" in result:
            return result["access_token"]

        error_desc = result.get("error_description", "Authentication failed")
        raise ValueError(
            f"Entra ID OBO Token Exchange Failed (Method: {settings.AUTH_METHOD}): {error_desc}"
        )


def get_token_provider() -> TokenProvider:
    """
    설정에 따라 적절한 TokenProvider를 반환하는 팩토리 함수입니다.
    이를 통해 클라우드 공급자나 인증 방식을 쉽게 전환할 수 있습니다.
    """
    # 현재는 Entra ID (Azure)만 지원하지만, 여기서 AWS/GCP 등으로 쉽게 확장 가능합니다.
    return EntraIDTokenProvider()
