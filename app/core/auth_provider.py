from abc import ABC, abstractmethod

import msal

from .config import settings


class TokenProvider(ABC):
    @abstractmethod
    async def get_obo_token(self, sso_token: str) -> str:
        """SSO 토큰을 사용자를 대신하는(OBO) 액세스 토큰으로 교환합니다."""
        pass

    @abstractmethod
    async def get_service_token(self) -> str:
        """서비스 자체의 ID(Managed Identity 등)를 사용하여 액세스 토큰을 가져옵니다."""
        pass


class EntraIDTokenProvider(TokenProvider):
    async def get_obo_token(self, sso_token: str) -> str:
        """
        SSO 토큰을 On-Behalf-Of(OBO) 액세스 토큰으로 교환합니다.
        주의: 이 방식은 사용자의 MFA 설정 등에 따라 로컬 개발 환경에서 실패할 수 있습니다.
        """
        scopes = ["https://management.core.windows.net//user_impersonation"]

        # OBO Flow를 위해 MSAL을 사용합니다.
        authority = (
            f"https://login.microsoftonline.com/{settings.TENANT_ID or 'common'}"
        )

        app = msal.ConfidentialClientApplication(
            settings.CLIENT_ID,
            authority=authority,
            client_credential=settings.CLIENT_SECRET,
        )

        # Teams에서 넘겨준 SSO 토큰을 ARM(Azure Resource Manager) 토큰으로 교환
        result = app.acquire_token_on_behalf_of(user_assertion=sso_token, scopes=scopes)

        if "access_token" in result:
            return result["access_token"]

        error_desc = result.get("error_description", "Authentication failed")
        if "AADSTS50076" in error_desc:
            error_desc = "MFA(다단계 인증)가 필요하여 OBO 토큰 교환에 실패했습니다. Managed Identity 방식을 권장합니다."

        raise ValueError(f"Entra ID OBO Token Exchange Failed: {error_desc}")

    async def get_service_token(self) -> str:
        """
        서비스(또는 개발자 CLI) 자체의 권한으로 토큰을 가져옵니다. (직방 방식)
        """
        from azure.identity.aio import DefaultAzureCredential, ChainedTokenCredential, ManagedIdentityCredential, AzureCliCredential
        
        if settings.TENANT_ID:
            credential = ChainedTokenCredential(
                ManagedIdentityCredential(),
                AzureCliCredential(tenant_id=settings.TENANT_ID)
            )
        else:
            credential = DefaultAzureCredential()

        token_info = await credential.get_token("https://management.azure.com/.default")
        await credential.close()
        return token_info.token


def get_token_provider() -> TokenProvider:
    """
    설정에 따라 적절한 TokenProvider를 반환하는 팩토리 함수입니다.
    이를 통해 클라우드 공급자나 인증 방식을 쉽게 전환할 수 있습니다.
    """
    # 현재는 Entra ID (Azure)만 지원하지만, 여기서 AWS/GCP 등으로 쉽게 확장 가능합니다.
    return EntraIDTokenProvider()
