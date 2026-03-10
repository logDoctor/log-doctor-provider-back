from fastapi import HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse

from ..repository import AgentPackageRepository


class DownloadPackageUseCase:
    """
    에이전트 패키지 파일을 안전하게 다운로드할 수 있도록 서빙하는 유즈케이스입니다.
    """

    def __init__(self, repository: AgentPackageRepository):
        self.repository = repository

    async def execute(self, version: str = "latest"):
        """업로드된 패키지 중 특정 버전 혹은 가장 최신 버전을 찾아 반환합니다."""
        try:
            package_info = await self.repository.get_by_version(version)

            if not package_info:
                raise HTTPException(
                    status_code=404, detail="Requested package version not found."
                )

            result = await self.repository.download(package_info.filename)
            filename = package_info.filename

            # 1. 파일 시스템인 경우 (문자열 경로 반환)
            if isinstance(result, str):
                return FileResponse(
                    path=result, filename=filename, media_type="application/zip"
                )

            # 2. Blob Storage인 경우 (StorageStreamDownloader 반환)
            # StorageStreamDownloader는 async iterator이므로 async generator로 래핑
            async def blob_stream():
                async for chunk in result.chunks():
                    yield chunk

            return StreamingResponse(
                blob_stream(),
                media_type="application/zip",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )

        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Requested package file not found: {filename}",
            ) from None
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while downloading the package: {str(e)}",
            ) from e
