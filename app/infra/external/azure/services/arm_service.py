from fnmatch import fnmatch

import httpx
import structlog

from app.core.auth.services.auth_provider import TokenProvider
from app.core.exceptions import ForbiddenException, InternalServerException
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
                raise ForbiddenException(
                    "AZURE_ACCESS_FORBIDDEN|You do not have permission to access the Azure subscription."
                )

            if resp.status_code != 200:
                raise Exception(
                    f"An error occurred while checking Azure permissions. (Code: {resp.status_code})"
                )

            permissions = resp.json().get("value", [])

            # 템플릿이 커스텀 역할 정의를 생성하므로, 두 가지 권한이 모두 필요합니다:
            # 1. Microsoft.Resources/deployments/write  — 배포 자체 권한 (Contributor)
            # 2. Microsoft.Authorization/roleDefinitions/write — 커스텀 역할 생성 권한 (Owner/UAA)
            required_actions = [
                "Microsoft.Resources/deployments/write",
                "Microsoft.Authorization/roleDefinitions/write",
            ]

            for required_action in required_actions:
                action_allowed = False
                for p in permissions:
                    actions = p.get("actions", [])
                    not_actions = p.get("notActions", [])

                    # Azure RBAC 패턴 매칭 (대소문자 무시, 글로브 와일드카드)
                    # 예: "Microsoft.Authorization/*/Write" 는 "Microsoft.Authorization/roleDefinitions/write"에 매칭
                    has_action = any(
                        fnmatch(required_action.lower(), a.lower())
                        for a in actions
                    )

                    # notActions 패턴도 동일하게 글로브 매칭
                    # Contributor의 notActions: ["Microsoft.Authorization/*/Write", ...]
                    is_denied = any(
                        fnmatch(required_action.lower(), na.lower())
                        for na in not_actions
                    )

                    if has_action and not is_denied:
                        action_allowed = True
                        break

                if not action_allowed:
                    raise ForbiddenException(
                        "INSUFFICIENT_SUB_PERMISSIONS|"
                        "Insufficient permissions for the Azure subscription. "
                        "Owner or User Access Administrator role is required "
                        "to create custom role definitions."
                    )

    async def list_resource_groups(
        self, access_token: str, subscription_id: str
    ) -> list[dict]:
        access_token = await self.token_provider.get_obo_token(access_token)

        url = (
            f"https://management.azure.com"
            f"/subscriptions/{subscription_id}"
            f"/resourcegroups"
            f"?api-version={self.api_version}"
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code != 200:
                self.logger.error(
                    "azure_list_rgs_failed",
                    status=response.status_code,
                    body=response.text,
                )
                raise InternalServerException(
                    f"Failed to list resource groups: {response.status_code}"
                )

            data = response.json()
            return [
                {
                    "id": rg.get("id"),
                    "name": rg.get("name"),
                    "location": rg.get("location"),
                }
                for rg in data.get("value", [])
                if rg.get("name")
            ]

    async def list_role_assignments(
        self, access_token: str, subscription_id: str
    ) -> list[dict]:
        """특정 구독의 역할 할당(Role Assignments) 목록을 조회합니다."""
        access_token = await self.token_provider.get_obo_token(access_token)

        url = (
            f"https://management.azure.com"
            f"/subscriptions/{subscription_id}"
            f"/providers/Microsoft.Authorization/roleAssignments"
            f"?api-version=2022-04-01&$filter=atScope()"
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code != 200:
                self.logger.error(
                    "azure_list_role_assignments_failed",
                    status=response.status_code,
                    body=response.text,
                )
                raise Exception(
                    f"Failed to list role assignments: {response.status_code}"
                )

            data = response.json()
            return data.get("value", [])

    async def get_function_app_principal_id(
        self, access_token: str, subscription_id: str, resource_group_name: str, function_app_name: str
    ) -> str | None:
        """Function App의 Managed Identity (Principal ID)를 조회합니다."""
        access_token = await self.token_provider.get_obo_token(access_token)

        url = (
            f"https://management.azure.com"
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group_name}"
            f"/providers/Microsoft.Web/sites/{function_app_name}"
            f"?api-version=2022-03-01"
        )
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 404:
                return None

            if response.status_code != 200:
                self.logger.error(
                    "azure_get_function_app_failed",
                    status=response.status_code,
                    body=response.text,
                )
                raise Exception(f"Failed to get Function App: {response.status_code}")

            data = response.json()
            # identity 필드 내부에서 principalId를 추출 (e.g. "identity": {"principalId": "..."})
            identity = data.get("identity")
            if identity and isinstance(identity, dict):
                return identity.get("principalId")
            return None

    async def delete_role_assignment(
        self, access_token: str, role_assignment_id: str
    ) -> None:
        """특정 역할 할당(Role Assignment)을 삭제합니다."""
        access_token = await self.token_provider.get_obo_token(access_token)

        # role_assignment_id는 일반적으로 absolute Azure 리소스 ID입니다: /subscriptions/...
        url = f"https://management.azure.com{role_assignment_id}?api-version=2022-04-01"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(url, headers=headers)

            if response.status_code in (200, 202, 204, 404):
                return

            self.logger.error(
                "azure_delete_role_assignment_failed",
                status=response.status_code,
                body=response.text,
                role_assignment_id=role_assignment_id
            )
            raise Exception(f"Failed to delete role assignment: {response.status_code}")
