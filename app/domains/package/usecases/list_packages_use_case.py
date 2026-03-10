from ..models import PackageInfo
from ..repository import AgentPackageRepository
from ..schemas import ListPackagesResponse


class ListPackagesUseCase:
    def __init__(self, repository: AgentPackageRepository):
        self.repository = repository

    async def execute(self) -> ListPackagesResponse:
        """업로드된 패키지 목록을 조회합니다."""
        items = await self.repository.list_all()
        return ListPackagesResponse(items=items)
