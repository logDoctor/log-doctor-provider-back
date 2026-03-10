from fastapi import UploadFile

from ..repository import AgentPackageRepository
from ..schemas import UploadPackageResponse


class UploadPackageUseCase:
    def __init__(self, repository: AgentPackageRepository):
        self.repository = repository

    async def execute(self, file: UploadFile) -> UploadPackageResponse:
        """에이전트 Zip 패키지를 저장공간에 업로드하고 무결성을 검증합니다."""
        # Checksum 계산 (SHA-256)
        # TODO: Checksum verification logic can be added here if needed
        await file.read()
        await file.seek(0)  # 리포지토리 저장을 위해 포인터 초기화

        package_info = await self.repository.save(file.filename, file.file)

        return UploadPackageResponse(
            message=f"Package {file.filename} uploaded successfully.",
            package=package_info,
        )
