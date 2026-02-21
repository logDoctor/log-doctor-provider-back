import httpx
from azure.core.credentials import AccessToken
import time

class DummyCredential:
    """
    azure-mgmt-resource SDK 등은 azure.core.credentials.TokenCredential 인터페이스를 요구합니다.
    우리는 이미 auth_provider를 통해 raw 토큰(문자열)을 구했으므로, 
    이를 SDK에 주입하기 위해 간단한 Wrapper 클래스를 만듭니다.
    """
    def __init__(self, token: str):
        self.token = token

    async def get_token(self, *scopes, **kwargs) -> AccessToken:
        # async SDK가 토큰을 요구할 때 우리가 이미 구한 토큰과 적당한 만료 시간(1시간 후)을 반환합니다.
        expires_on = int(time.time()) + 3600 
        return AccessToken(self.token, expires_on)

class AzureRestClient:
    """
    Azure ARM REST API Client Factory.
    Provides authenticated httpx client sessions.
    """

    @staticmethod
    def get_client(access_token: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url="https://management.azure.com",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
