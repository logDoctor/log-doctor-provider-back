from abc import ABC, abstractmethod


class AzureArmService(ABC):
    """Azure 리소스 관리(Management Plane) 서비스 인터페이스"""

    @abstractmethod
    async def delete_resource_group(
        self, access_token: str, subscription_id: str, resource_group_name: str
    ) -> None:
        """리소스 그룹 삭제를 요청합니다."""
        pass

    @abstractmethod
    async def check_resource_group_exists(
        self, access_token: str, subscription_id: str, resource_group_name: str
    ) -> bool:
        """리소스 그룹의 존재 여부를 확인합니다."""
        pass

    @abstractmethod
    async def update_function_app_settings(
        self,
        access_token: str,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        settings_to_update: dict[str, str],
    ) -> None:
        """Function App의 앱 설정을 변경합니다."""
        pass

    @abstractmethod
    async def list_resource_groups(
        self, access_token: str, subscription_id: str
    ) -> list[dict]:
        """조회 가능한 리소스 그룹 명단을 반환합니다."""
        pass

    @abstractmethod
    async def check_deployment_permission(
        self, sso_token: str, subscription_id: str
    ) -> None:
        """사용자의 배포 권한을 확인합니다. 권한이 없으면 예외를 발생시킵니다."""
        pass
