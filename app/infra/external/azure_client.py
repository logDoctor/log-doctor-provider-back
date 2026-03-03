import httpx


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
