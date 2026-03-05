from fastapi import Depends, File, UploadFile
from fastapi_restful.cbv import cbv

from app.core.auth.guards import check_admin
from app.core.auth.guards.download_guard import check_download_token
from app.core.routing import APIRouter

from .dependencies import (
    get_download_package_use_case,
    get_list_packages_use_case,
    get_package_use_case,
    get_upload_package_use_case,
)
from .models import PackageInfo
from .usecases import (
    DownloadPackageUseCase,
    GetPackageUseCase,
    ListPackagesUseCase,
    UploadPackageUseCase,
)

# 에이전트 패키지 관리 API
router = APIRouter(prefix="/packages", tags=["Packages"])


@cbv(router)
class PackageAdminRouter:
    def __init__(
        self,
        upload_use_case: UploadPackageUseCase = Depends(get_upload_package_use_case),
        list_use_case: ListPackagesUseCase = Depends(get_list_packages_use_case),
        get_package_use_case: GetPackageUseCase = Depends(get_package_use_case),
        download_use_case: DownloadPackageUseCase = Depends(get_download_package_use_case),
    ):
        self.upload_use_case = upload_use_case
        self.list_use_case = list_use_case
        self.get_package_use_case = get_package_use_case
        self.download_use_case = download_use_case

    @router.api_route("/download", methods=["GET", "HEAD"], dependencies=[Depends(check_download_token)])
    async def download_package_by_version(self, version: str = "latest"):
        """에이전트 패키지를 토큰을 사용하여 버전별로 다운로드합니다. (Client Setup Template용)"""
        return await self.download_use_case.execute(version)

    @router.post("/upload", dependencies=[Depends(check_admin)])
    async def upload_package(self, file: UploadFile = File(...)):
        """에이전트 Zip 패키지를 업로드합니다. (운영자 전용)"""
        return await self.upload_use_case.execute(file)

    @router.get("/", dependencies=[Depends(check_admin)])
    async def list_packages(self, version: str | None = None):
        """패키지 목록 또는 특정 버전을 조회합니다. (운영자 전용)"""
        if version:
            return await self.get_package_use_case.execute(version)
        return await self.list_use_case.execute()
