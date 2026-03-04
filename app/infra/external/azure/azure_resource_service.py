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
        self, subscription_id: str, resource_group_name: str
    ) -> bool:
        """Managed Identity로 리소스 그룹의 존재 여부를 확인합니다."""
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
        self, subscription_id: str, resource_group_name: str
    ) -> bool:
        url = (
            f"https://management.azure.com"
            f"/subscriptions/{subscription_id}"
            f"/resourcegroups/{resource_group_name}"
            f"?api-version={ARM_API_VERSION}"
        )

        credential = None
        try:
            credential = DefaultAzureCredential()
            token = await credential.get_token("https://management.azure.com/.default")

            async with httpx.AsyncClient() as client:
                response = await client.head(
                    url,
                    headers={"Authorization": f"Bearer {token.token}"},
                )

                # ARM API HEAD 요청은 204나 200이 올 수 있음. 
                # 404인 경우에만 "존재하지 않음"으로 간주하고,
                # 401, 403 등 권한 문제나 일시적인 오류는 안전하게 "존재함(True)"으로 간주 (삭제 무단 확정 방지)
                exists = response.status_code != 404
                if response.status_code >= 400 and response.status_code != 404:
                    logger.warning(
                        "Resource group check unexpected status",
                        status_code=response.status_code,
                        resource_group_name=resource_group_name
                    )
                logger.info(
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
        finally:
            if credential:
                await credential.close()
