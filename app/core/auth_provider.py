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
        scopes = ["https://management.core.windows.net//user_impersonation"]

        if settings.AUTH_METHOD == "managed_identity":
            from azure.identity.aio import DefaultAzureCredential
            
            # 개발자의 로컬 환경 (az login) 혹은 Azure 리소스의 Managed Identity 권한을 사용하여
            # 아까 변경했던 tenant_id 고정값을 지우고 기본 설정으로 되돌립니다.
            # 이제 설치하신 azd(Azure Developer CLI)의 로그인 정보를 자동으로 가져옵니다.
            credential = DefaultAzureCredential()
            token_info = await credential.get_token("https://management.azure.com/.default")
            await credential.close()
            return token_info.token

        # AUTH_METHOD == "secret" 인 경우, 원래의 OBO 흐름을 사용합니다.
        authority = (
            f"https://login.microsoftonline.com/{settings.TENANT_ID or 'common'}"
        )

        app = msal.ConfidentialClientApplication(
            settings.CLIENT_ID,
            authority=authority,
            client_credential=settings.CLIENT_SECRET,
        )

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
