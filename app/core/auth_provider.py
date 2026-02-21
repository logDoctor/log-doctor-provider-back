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
        
        # MFA(AADSTS50076) 챌린지 감지 및 claims 추출
        if "AADSTS50076" in error_desc or result.get("error") == "interaction_required":
            claims = result.get("claims")
            if claims:
                # 관례적으로 에러 메시지에 claims를 포함하거나, 호출 측에서 result를 직접 볼 수 있게 처리해야 함
                # 여기선 ValueError에 특수 접두사를 붙여 상위 레이어에서 파싱하기 쉽게 만듭니다.
                raise ValueError(f"MFA_REQUIRED|{claims}")
            
            error_desc = "MFA(다단계 인증)가 필요하여 OBO 토큰 교환에 실패했습니다. (Claims missing)"

        raise ValueError(f"Entra ID OBO Token Exchange Failed: {error_desc}")

    async def get_service_token(self) -> str:
        """
        서비스(또는 개발자 CLI/Secret) 자체의 권한으로 토큰을 가져옵니다. (직방 방식)
        로컬 개발 시 az login 없이도 .env의 Secret 정보를 사용하여 인증할 수 있도록 개선했습니다.
        """
        from azure.identity.aio import (
            ChainedTokenCredential, 
            ManagedIdentityCredential, 
            AzureCliCredential,
            ClientSecretCredential
        )
        
        credentials = []
        
        # 1. 운영 환경: Managed Identity (1순위)
        credentials.append(ManagedIdentityCredential())

        # 2. 로컬 개발 환경: Azure CLI (2순위 - 방금 팀장님이 수행하신 az login 세션을 사용)
        if settings.TENANT_ID:
            credentials.append(AzureCliCredential(tenant_id=settings.TENANT_ID))
        else:
            credentials.append(AzureCliCredential())

        # 3. 로컬 개발 환경: .env의 Client Secret (3순위 - 마지막 수단)
        if settings.CLIENT_ID and settings.CLIENT_SECRET and settings.TENANT_ID:
            credentials.append(ClientSecretCredential(
                tenant_id=settings.TENANT_ID,
                client_id=settings.CLIENT_ID,
                client_secret=settings.CLIENT_SECRET
            ))

        credential = ChainedTokenCredential(*credentials)

        try:
            token_info = await credential.get_token("https://management.azure.com/.default")
            await credential.close()
            return token_info.token
        except Exception as e:
            await credential.close()
            raise e


def get_token_provider() -> TokenProvider:
    """
    설정에 따라 적절한 TokenProvider를 반환하는 팩토리 함수입니다.
    이를 통해 클라우드 공급자나 인증 방식을 쉽게 전환할 수 있습니다.
    """
    # 현재는 Entra ID (Azure)만 지원하지만, 여기서 AWS/GCP 등으로 쉽게 확장 가능합니다.
    return EntraIDTokenProvider()
