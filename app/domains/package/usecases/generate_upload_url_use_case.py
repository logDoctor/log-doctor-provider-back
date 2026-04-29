import re

from app.domains.package.repository import AgentPackageRepository


class GeneratePackageUploadUrlUseCase:
    def __init__(self, repository: AgentPackageRepository):
        self.repository = repository

    async def execute(self, filename: str) -> str:
        # 파일명 검증: 알파벳, 숫자, 점, 하이픈만 허용하며 .zip으로 끝나야 함
        if not re.match(r"^[a-zA-Z0-9.-]+\.zip$", filename):
            raise ValueError(
                "Invalid filename. Only alphanumeric, dots, and hyphens are allowed, and must end with .zip"
            )

        try:
            return await self.repository.generate_upload_url(filename)
        except NotImplementedError as e:
            # 로컬 파일 시스템 등 지원하지 않는 환경일 경우
            raise ValueError(str(e)) from e
