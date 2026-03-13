from app.core.config import settings

from .repository import (
    AgentPackageRepository,
    BlobStorageAgentPackageRepository,
    FileSystemAgentPackageRepository,
)
from .usecases import (
    DownloadPackageUseCase,
    GetPackageUseCase,
    ListPackagesUseCase,
    UploadPackageUseCase,
)


def get_agent_package_repository() -> AgentPackageRepository:
    if settings.STORAGE_TYPE == "blob" and settings.BLOB_STORAGE_ACCOUNT_NAME:
        return BlobStorageAgentPackageRepository(
            account_name=settings.BLOB_STORAGE_ACCOUNT_NAME,
            container_name=settings.AGENT_PACKAGE_CONTAINER,
        )
    return FileSystemAgentPackageRepository()


def get_upload_package_use_case() -> UploadPackageUseCase:
    return UploadPackageUseCase(get_agent_package_repository())


def get_list_packages_use_case() -> ListPackagesUseCase:
    return ListPackagesUseCase(get_agent_package_repository())


def get_package_use_case() -> GetPackageUseCase:
    return GetPackageUseCase(get_agent_package_repository())


def get_download_package_use_case() -> DownloadPackageUseCase:
    return DownloadPackageUseCase(get_agent_package_repository())
