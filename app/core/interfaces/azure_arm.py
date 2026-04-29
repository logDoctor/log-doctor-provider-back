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

    @abstractmethod
    async def list_role_assignments(
        self, access_token: str, subscription_id: str
    ) -> list[dict]:
        """특정 구독의 역할 할당(Role Assignments) 목록을 조회합니다."""
        pass

    @abstractmethod
    async def get_function_app_principal_id(
        self,
        access_token: str,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
    ) -> str | None:
        """Function App의 Managed Identity (Principal ID)를 조회합니다."""
        pass

    @abstractmethod
    async def delete_role_assignment(
        self, access_token: str, role_assignment_id: str
    ) -> None:
        """특정 역할 할당(Role Assignment)을 삭제합니다."""
        pass

    @abstractmethod
    async def list_resources_by_tag(
        self, access_token: str, subscription_id: str, tag_name: str, tag_value: str
    ) -> list[dict]:
        """특정 태그가 포함된 리소스 목록을 조회합니다."""
        pass
