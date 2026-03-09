from abc import ABC, abstractmethod

import httpx
import structlog

from app.core.auth.services.auth_provider import TokenProvider

from .azure_client import AzureRestClient

logger = structlog.get_logger()

ARM_API_VERSION = "2021-04-01"


# 1. Interface
class AzureResourceService(ABC):
    """Azure 리소스 관리 서비스 인터페이스"""

    @abstractmethod
    async def delete_resource_group(
        self, access_token: str, subscription_id: str, resource_group_name: str
    ) -> str:
        """OBO 토큰으로 리소스 그룹 삭제를 요청합니다.

        Returns:
            'ACCEPTED' - 삭제 요청 수락됨 (비동기 처리)
            'NOT_FOUND' - 리소스 그룹이 이미 존재하지 않음
            'FAILED' - 삭제 요청 실패
        """
        pass

    @abstractmethod
    async def check_resource_group_exists(
        self, access_token: str, subscription_id: str, resource_group_name: str
    ) -> bool:
        """액세스 토큰으로 리소스 그룹의 존재 여부를 확인합니다."""
        pass

    @abstractmethod
    async def update_function_app_settings(
        self,
        access_token: str,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        settings_to_update: dict[str, str],
    ) -> str:
        """Function App의 앱 설정을 변경합니다.

        Returns:
            'SUCCESS' - 설정 변경 성공
            'NOT_FOUND' - Function App을 찾을 수 없음
            'FAILED' - 설정 변경 실패
        """
        pass

    @abstractmethod
    async def check_deployment_permission(
        self, sso_token: str, subscription_id: str
    ) -> tuple[bool, str | None]:
        """사용자가 SSO 토큰을 통해 해당 구독에 대해 실제 리소스를 배포할 권한(Contributor 이상)이 있는지 확인합니다."""
        pass


# 2. Implementation
class AzureResourceServiceImpl(AzureResourceService):
    """Azure ARM REST API 기반 리소스 관리 서비스 구현체"""

    def __init__(self, token_provider: TokenProvider):
        self.token_provider = token_provider

    async def delete_resource_group(
        self, access_token: str, subscription_id: str, resource_group_name: str
    ) -> str:
        url = (
            f"/subscriptions/{subscription_id}"
            f"/resourcegroups/{resource_group_name}"
            f"?api-version={ARM_API_VERSION}"
        )

        try:
            async with AzureRestClient.get_client(access_token) as client:
                response = await client.delete(url)

                if response.status_code in (200, 202, 204):
                    logger.info(
                        "Resource group deletion accepted",
                        subscription_id=subscription_id,
                        resource_group_name=resource_group_name,
                    )
                    return "ACCEPTED"
                elif response.status_code == 404:
                    logger.info(
                        "Resource group already deleted",
                        resource_group_name=resource_group_name,
                    )
                    return "NOT_FOUND"
                else:
                    logger.error(
                        "Resource group deletion failed",
                        status_code=response.status_code,
                        body=response.text,
                    )
                    return "FAILED"
        except Exception as e:
            logger.error("Resource group deletion error", error=str(e))
            return "FAILED"

    async def check_resource_group_exists(
        self, access_token: str, subscription_id: str, resource_group_name: str
    ) -> bool:
        url = (
            f"https://management.azure.com"
            f"/subscriptions/{subscription_id}"
            f"/resourcegroups/{resource_group_name}"
            f"?api-version={ARM_API_VERSION}"
        )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                # ARM API HEAD 요청은 204나 200이 올 수 있음.
                # 404인 경우에만 "존재하지 않음"으로 간주
                exists = response.status_code != 404

                # 401, 403 등 권한 오류는 로깅하고 '존재함'으로 처리하여 오판 방지
                if response.status_code >= 400 and response.status_code != 404:
                    logger.warning(
                        "Resource group check unexpected status",
                        status_code=response.status_code,
                        resource_group_name=resource_group_name,
                        response_body=response.text
                        if hasattr(response, "text")
                        else "",
                    )

                logger.debug(
                    "Resource group existence check",
                    resource_group_name=resource_group_name,
                    exists=exists,
                    status_code=response.status_code,
                )
                return exists
        except Exception as e:
            logger.error("Resource group existence check error", error=str(e))
            # 확인 실패 시 안전하게 '존재한다'로 간주 (삭제 확정 방지)
            return True

    async def update_function_app_settings(
        self,
        access_token: str,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        settings_to_update: dict[str, str],
    ) -> str:
        """ARM REST API로 Function App의 앱 설정을 변경합니다."""
        # 1. 기존 설정 조회
        list_url = (
            f"https://management.azure.com"
            f"/subscriptions/{subscription_id}"
            f"/resourceGroups/{resource_group_name}"
            f"/providers/Microsoft.Web/sites/{function_app_name}"
            f"/config/appsettings/list"
            f"?api-version=2022-03-01"
        )

        try:
            async with httpx.AsyncClient() as client:
                # POST로 기존 설정 목록 조회
                list_response = await client.post(
                    list_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if list_response.status_code == 404:
                    logger.warning(
                        "Function App not found", function_app_name=function_app_name
                    )
                    return "NOT_FOUND"

                if list_response.status_code != 200:
                    logger.error(
                        "Failed to list app settings",
                        status_code=list_response.status_code,
                        body=list_response.text,
                    )
                    return "FAILED"

                current_settings = list_response.json().get("properties", {})

                # 2. 새 설정 병합
                current_settings.update(settings_to_update)

                # 3. 설정 적용 (PUT)
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

                if put_response.status_code in (200, 201):
                    logger.info(
                        "Function App settings updated",
                        function_app_name=function_app_name,
                        updated_keys=list(settings_to_update.keys()),
                    )
                    return "SUCCESS"
                else:
                    logger.error(
                        "Failed to update app settings",
                        status_code=put_response.status_code,
                        body=put_response.text,
                    )
                    return "FAILED"

        except Exception as e:
            logger.error("Function App settings update error", error=str(e))
            return "FAILED"

    async def check_deployment_permission(
        self, sso_token: str, subscription_id: str
    ) -> tuple[bool, str | None]:
        """SSO 토큰을 OBO 토큰으로 교체한 후 ARM API를 호출하여 배포 권한을 검증합니다."""
        try:
            # 0. OBO 토큰 획득
            access_token = await self.token_provider.get_obo_token(sso_token)

            # 1. 권한 조회 API 호출 (Microsoft.Authorization/permissions)
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
                    return (
                        False,
                        "해당 Azure 구독에 접근할 권한이 없습니다. (403 Forbidden)",
                    )

                if resp.status_code != 200:
                    logger.error(
                        "Azure Permission API Failed",
                        code=resp.status_code,
                        text=resp.text,
                    )
                    return (
                        False,
                        f"Azure 권한 확인 중 오류가 발생했습니다. (Code: {resp.status_code})",
                    )

                permissions = resp.json().get("value", [])

                # 2. 필수 권한(Actions) 보유 여부 확인
                # 리소스 배포를 위해 최소한 'Microsoft.Resources/deployments/write' 권한이 필요합니다.
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
                    return (
                        False,
                        "Azure 구독에 대한 '기여자(Contributor)' 이상의 권한이 부족합니다. 구독 소유자에게 권한 할당을 요청하세요.",
                    )

                return True, None

        except Exception as e:
            logger.error("Azure RBAC Check System Error", error=str(e))
            return False, f"시스템 오류로 배포 권한을 확인할 수 없습니다: {str(e)}"
