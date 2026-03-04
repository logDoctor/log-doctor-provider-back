from abc import ABC, abstractmethod

import httpx
import structlog
from azure.identity.aio import DefaultAzureCredential

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


# 2. Implementation
class AzureResourceServiceImpl(AzureResourceService):
    """Azure ARM REST API 기반 리소스 관리 서비스 구현체"""

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
                        response_body=response.text if hasattr(response, 'text') else ""
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
                    logger.warning("Function App not found", function_app_name=function_app_name)
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
