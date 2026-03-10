import httpx
import structlog

from app.core.auth.services.auth_provider import TokenProvider
from app.core.interfaces.azure_arm import AzureArmService
from app.infra.external.azure.clients import AzureArmClient


class AzureArmServiceImpl(AzureArmService):
    """Azure ARM REST API 기반 리소스 관리 서비스 구현체"""

    def __init__(
        self,
        token_provider: TokenProvider,
        arm_client: AzureArmClient,
        logger: structlog.BoundLogger,
    ):
        self.token_provider = token_provider
        self.arm_client = arm_client
        self.logger = logger
        self.api_version = "2021-04-01"

    async def delete_resource_group(
        self, access_token: str, subscription_id: str, resource_group_name: str
    ) -> None:
        url = (
            f"/subscriptions/{subscription_id}"
            f"/resourcegroups/{resource_group_name}"
            f"?api-version={self.api_version}"
        )

        async with self.arm_client.get_client(access_token) as client:
            response = await client.delete(url)

            if response.status_code in (200, 202, 204, 404):
                # 404 is considered success for deletion (already gone)
                return

            raise Exception(
                f"Resource group deletion failed: {response.status_code} {response.text}"
            )

    async def check_resource_group_exists(
        self, access_token: str, subscription_id: str, resource_group_name: str
    ) -> bool:
        url = (
            f"https://management.azure.com"
            f"/subscriptions/{subscription_id}"
            f"/resourcegroups/{resource_group_name}"
            f"?api-version={self.api_version}"
        )

        async with httpx.AsyncClient() as client:
            response = await client.head(
                url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            return response.status_code != 404

    async def update_function_app_settings(
        self,
        access_token: str,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        settings_to_update: dict[str, str],
    ) -> None:
        list_url = (
            f"https://management.azure.com"
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group_name}"
            f"/providers/Microsoft.Web/sites/{function_app_name}"
            f"/config/appsettings/list"
            f"?api-version=2022-03-01"
        )

        async with httpx.AsyncClient() as client:
            list_response = await client.post(
                list_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if list_response.status_code != 200:
                raise Exception(
                    f"Failed to list app settings: {list_response.status_code} {list_response.text}"
                )

            current_settings = list_response.json().get("properties", {})
            current_settings.update(settings_to_update)

            put_url = (
                f"https://management.azure.com"
                f"/subscriptions/{subscription_id}"
                f"/resourceGroups/{resource_group_name}"
                f"/providers/Microsoft.Web/sites/{function_app_name}"
                f"/config/appsettings"
                f"?api-version=2022-03-01"
            )

            put_response = await client.put(
                put_url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"properties": current_settings},
            )

            if put_response.status_code not in (200, 201):
                raise Exception(
                    f"Failed to update app settings: {put_response.status_code} {put_response.text}"
                )

    async def check_deployment_permission(
        self, sso_token: str, subscription_id: str
    ) -> None:
        access_token = await self.token_provider.get_obo_token(sso_token)

        url = (
            f"https://management.azure.com"
            f"/subscriptions/{subscription_id}"
            f"/providers/Microsoft.Authorization/permissions"
            f"?api-version=2022-04-01"
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)

            if resp.status_code == 403:
                raise Exception(
                    "You do not have permission to access the Azure subscription. (403 Forbidden)"
                )

            if resp.status_code != 200:
                raise Exception(
                    f"An error occurred while checking Azure permissions. (Code: {resp.status_code})"
                )

            permissions = resp.json().get("value", [])
            required_action = "Microsoft.Resources/deployments/write"

            can_deploy = False
            for p in permissions:
                actions = p.get("actions", [])
                if (
                    "*" in actions
                    or required_action in actions
                    or "Microsoft.Resources/*" in actions
                ):
                    can_deploy = True
                    break

            if not can_deploy:
                raise Exception(
                    "Insufficient permissions for the Azure subscription (Contributor or higher required). Please request role assignment from the subscription owner."
                )
