from ..models import PackageInfo
from ..repository import AgentPackageRepository


class GetPackageUseCase:
    """
    특정 버전 혹은 최신 버전의 패키지 정보를 효율적으로 조회하는 유즈케이스입니다.
    """

    def __init__(self, repository: AgentPackageRepository):
        self.repository = repository

    async def execute(self, version: str = "latest") -> PackageInfo | None:
        """업로드된 패키지 중 특정 버전 혹은 가장 최신 버전을 반환합니다."""
        if version == "latest":
            return await self.repository.get_latest()

        return await self.repository.get_by_version(version)
