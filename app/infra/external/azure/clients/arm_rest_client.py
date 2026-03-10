import httpx


class AzureArmClient:
    """
    Azure ARM REST API Client Factory.
    Provides authenticated httpx client sessions.
    """

    def get_client(self, access_token: str) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url="https://management.azure.com",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
