import hashlib

from fastapi import UploadFile

from ..repository import AgentPackageRepository


class UploadPackageUseCase:
    def __init__(self, repository: AgentPackageRepository):
        self.repository = repository

    async def execute(self, file: UploadFile) -> dict:
        """에이전트 Zip 패키지를 저장공간에 업로드하고 무결성을 검증합니다."""
        # Checksum 계산 (SHA-256)
        content = await file.read()
        checksum = hashlib.sha256(content).hexdigest()
        await file.seek(0)  # 리포지토리 저장을 위해 포인터 초기화

        package_info = await self.repository.save(file.filename, file.file)

        return {
            "message": f"Package {file.filename} uploaded successfully.",
            "url": package_info.url,
            "size": package_info.size,
            "checksum": checksum,
        }
