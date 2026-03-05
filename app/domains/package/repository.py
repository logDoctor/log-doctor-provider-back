import logging
import os
import shutil
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from azure.core.exceptions import ResourceExistsError
from azure.identity.aio import DefaultAzureCredential
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient
from fastapi.concurrency import run_in_threadpool

from .models import PackageInfo

logger = logging.getLogger(__name__)


class AgentPackageRepository(ABC):
    """에이전트 패키지 저장소 인터페이스입니다."""

    @abstractmethod
    async def save(self, filename: str, file_content) -> PackageInfo:
        """패키지를 저장소에 저장합니다."""
        pass

    @abstractmethod
    async def list_all(self) -> list[PackageInfo]:
        """모든 패키지 목록을 조회합니다."""
        pass

    @abstractmethod
    async def get_latest(self) -> PackageInfo | None:
        """가장 최신 패키지를 조회합니다."""
        pass

    @abstractmethod
    async def get_by_version(self, version: str) -> PackageInfo | None:
        """특정 버전의 패키지를 조회합니다."""
        pass

    @abstractmethod
    async def download(self, filename: str):
        """패키지 파일의 내용을 읽기 위한 스트림 또는 경로를 반환합니다."""
        pass

    @abstractmethod
    async def generate_download_url(self, filename: str) -> str:
        """Azure가 직접 접근 가능한 다운로드 URL을 생성합니다."""
        pass


class FileSystemAgentPackageRepository(AgentPackageRepository):
    """로컬 파일 시스템을 사용하는 에이전트 패키지 저장소 구현체입니다."""

    def __init__(self, packages_dir: str = "packages"):
        self.packages_dir = packages_dir
        if not os.path.exists(self.packages_dir):
            os.makedirs(self.packages_dir)

    async def save(self, filename: str, file_content) -> PackageInfo:
        file_path = os.path.join(self.packages_dir, filename)
        await run_in_threadpool(self._save_sync, file_path, file_content)

        stats = os.stat(file_path)
        return PackageInfo(
            filename=filename,
            size=stats.st_size,
            url=f"/api/v1/packages/download/{filename}",
            version=PackageInfo.parse_version(filename),
        )

    async def list_all(self) -> list[PackageInfo]:
        return await run_in_threadpool(self._list_sync)

    async def get_latest(self) -> PackageInfo | None:
        return await run_in_threadpool(self._get_latest_sync)

    async def get_by_version(self, version: str) -> PackageInfo | None:
        return await run_in_threadpool(self._get_by_version_sync, version)

    async def download(self, filename: str) -> str:
        """파일 시스템에서의 다운로드는 파일 경로를 반환합니다."""
        file_path = os.path.join(self.packages_dir, filename)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        return file_path

    async def generate_download_url(self, filename: str) -> str:
        """로컬 환경에서는 서버 프록시 URL을 반환합니다."""
        return f"/api/v1/packages/download/{filename}"

    def _get_package_info(self, filename: str) -> PackageInfo:
        file_path = os.path.join(self.packages_dir, filename)
        stats = os.stat(file_path)
        return PackageInfo(
            filename=filename,
            size=stats.st_size,
            url=f"/api/v1/packages/download/{filename}",
            version=PackageInfo.parse_version(filename),
        )

    def _save_sync(self, path: str, content):
        with open(path, "wb") as buffer:
            shutil.copyfileobj(content, buffer)

    def _list_sync(self) -> list[PackageInfo]:
        if not os.path.exists(self.packages_dir):
            return []
        filenames = [f for f in os.listdir(self.packages_dir) if f.endswith(".zip")]
        filenames.sort(reverse=True)
        return [self._get_package_info(f) for f in filenames]

    def _get_latest_sync(self) -> PackageInfo | None:
        if not os.path.exists(self.packages_dir):
            return None
        filenames = [f for f in os.listdir(self.packages_dir) if f.endswith(".zip")]
        if not filenames:
            return None
        # semver 기준 최신 버전 선택
        packages = [self._get_package_info(f) for f in filenames]
        packages.sort(key=lambda p: [int(x) for x in p.version.split(".") if x.isdigit()], reverse=True)
        return packages[0]

    def _get_by_version_sync(self, version: str) -> PackageInfo | None:
        if not os.path.exists(self.packages_dir):
            return None
        filenames = os.listdir(self.packages_dir)
        for f in filenames:
            if f.endswith(".zip") and version in f:
                return self._get_package_info(f)
        return None


class BlobStorageAgentPackageRepository(AgentPackageRepository):
    """Azure Blob Storage를 사용하는 에이전트 패키지 저장소 구현체입니다."""

    def __init__(self, account_name: str, container_name: str):
        self.account_url = f"https://{account_name}.blob.core.windows.net"
        self.container_name = container_name
        self._client = None
        self._container_client = None

    async def _get_container_client(self):
        from app.core.config import settings

        if not self._container_client:
            if settings.AZURE_STORAGE_CONNECTION_STRING:
                logger.info("Using Azure Storage Connection String")
                self._client = BlobServiceClient.from_connection_string(
                    settings.AZURE_STORAGE_CONNECTION_STRING
                )
            else:
                logger.info("Using DefaultAzureCredential for Blob Storage")
                credential = DefaultAzureCredential()
                self._client = BlobServiceClient(
                    self.account_url, credential=credential
                )

            self._container_client = self._client.get_container_client(
                self.container_name
            )

            import contextlib

            with contextlib.suppress(ResourceExistsError):
                await self._container_client.create_container()
        return self._container_client

    async def save(self, filename: str, file_content) -> PackageInfo:
        container_client = await self._get_container_client()
        blob_client = container_client.get_blob_client(filename)

        # Binary content를 직접 업로드
        await blob_client.upload_blob(file_content, overwrite=True)

        properties = await blob_client.get_blob_properties()
        return PackageInfo(
            filename=filename,
            size=properties.size,
            url=f"/api/v1/packages/download/{filename}",
            version=PackageInfo.parse_version(filename),
        )

    async def list_all(self) -> list[PackageInfo]:
        container_client = await self._get_container_client()
        packages = []
        async for blob in container_client.list_blobs():
            if blob.name.endswith(".zip"):
                packages.append(
                    PackageInfo(
                        filename=blob.name,
                        size=blob.size,
                        url=f"/api/v1/packages/download/{blob.name}",
                        version=PackageInfo.parse_version(blob.name),
                    )
                )
        packages.sort(key=lambda x: x.filename, reverse=True)
        return packages

    async def get_latest(self) -> PackageInfo | None:
        packages = await self.list_all()
        if not packages:
            return None
        # semver 기준 최신 버전 선택
        packages.sort(key=lambda p: [int(x) for x in p.version.split(".") if x.isdigit()], reverse=True)
        return packages[0]

    async def get_by_version(self, version: str) -> PackageInfo | None:
        container_client = await self._get_container_client()
        async for blob in container_client.list_blobs():
            if blob.name.endswith(".zip") and version in blob.name:
                return PackageInfo(
                    filename=blob.name,
                    size=blob.size,
                    url=f"/api/v1/packages/download/{blob.name}",
                    version=PackageInfo.parse_version(blob.name),
                )
        return None

    async def download(self, filename: str):
        """Blob Storage에서의 다운로드는 스트림을 반환합니다."""
        container_client = await self._get_container_client()
        blob_client = container_client.get_blob_client(filename)

        if not await blob_client.exists():
            raise FileNotFoundError(f"Blob not found: {filename}")

        stream = await blob_client.download_blob()
        return stream

    async def generate_download_url(self, filename: str) -> str:
        """Blob SAS URL을 생성하여 Azure가 직접 접근 가능한 URL을 반환합니다."""
        from app.core.config import settings

        # Connection String에서 Account Key 추출
        account_name = None
        account_key = None
        if settings.AZURE_STORAGE_CONNECTION_STRING:
            parts = dict(
                part.split("=", 1)
                for part in settings.AZURE_STORAGE_CONNECTION_STRING.split(";")
                if "=" in part
            )
            account_name = parts.get("AccountName")
            account_key = parts.get("AccountKey")

        if not account_name or not account_key:
            # Connection String이 없으면 서버 프록시 URL로 폴백
            logger.warning("Account key not found, falling back to proxy URL")
            return f"/api/v1/packages/download/{filename}"

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self.container_name,
            blob_name=filename,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(UTC) + timedelta(days=30),
        )

        return f"https://{account_name}.blob.core.windows.net/{self.container_name}/{filename}?{sas_token}"
