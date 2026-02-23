from ..models import PackageInfo
from ..repository import AgentPackageRepository


class ListPackagesUseCase:
    def __init__(self, repository: AgentPackageRepository):
        self.repository = repository

    async def execute(self) -> list[PackageInfo]:
        """업로드된 패키지 목록을 조회합니다."""
        return await self.repository.list_all()
