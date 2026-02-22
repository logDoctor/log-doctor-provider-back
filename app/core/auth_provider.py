from abc import ABC, abstractmethod
import msal
import structlog

from .config import settings

logger = structlog.get_logger()


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
        SSO 토큰을 사용자를 대신하는(OBO) 액세스 토큰으로 교환합니다.
        """
        authority = f"https://login.microsoftonline.com/{settings.TENANT_ID or 'common'}"
        client_credential = None
        if settings.AUTH_METHOD == "secret":
            client_credential = settings.CLIENT_SECRET

        app = msal.ConfidentialClientApplication(
            settings.CLIENT_ID,
            authority=authority,
            client_credential=client_credential,
        )

        scopes = ["https://management.azure.com/.default"]
        sso_token = sso_token.replace("Bearer ", "").strip()

        logger.debug("Attempting OBO Token Exchange")

        # 사용자의 SSO 토큰을 사용하여 OBO 토큰 획득
        result = app.acquire_token_on_behalf_of(user_assertion=sso_token, scopes=scopes)

        if "access_token" in result:
            return result["access_token"]

        raise ValueError(
            f"Entra ID OBO Token Exchange Failed: {result.get('error_description', 'Authentication failed')}"
        )

    async def get_service_token(self) -> str:
        """
        DefaultAzureCredential을 사용하여 토큰을 가져옵니다.
        1. 운영 환경: Managed Identity
        2. 로컬 개발: Azure CLI (az login) 또는 Environment Variables
        """
        from azure.identity.aio import DefaultAzureCredential
        
        # Managed Identity 사용 시 특정 Client ID를 명시적으로 지정
        credential = DefaultAzureCredential(
            managed_identity_client_id=settings.MANAGED_IDENTITY_CLIENT_ID if settings.AUTH_METHOD == "managed_identity" else None
        )

        try:
            token_info = await credential.get_token("https://management.azure.com/.default")
            return token_info.token
        except Exception as e:
            logger.error(f"Failed to acquire token via DefaultAzureCredential: {str(e)}")
            raise e
        finally:
            await credential.close()


def get_token_provider() -> TokenProvider:
    """
    설정에 따라 적절한 TokenProvider를 반환하는 팩토리 함수입니다.
    이를 통해 클라우드 공급자나 인증 방식을 쉽게 전환할 수 있습니다.
    """
    # 현재는 Entra ID (Azure)만 지원하지만, 여기서 AWS/GCP 등으로 쉽게 확장 가능합니다.
    return EntraIDTokenProvider()
