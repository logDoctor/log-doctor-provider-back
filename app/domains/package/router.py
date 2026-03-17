from fastapi import Depends, File, UploadFile
from fastapi_restful.cbv import cbv

from app.core.auth.guards import admin_verify_guard, get_current_identity
from app.core.auth.guards.download_guard import check_download_token
from app.core.routing import APIRouter

from .dependencies import (
    get_download_package_use_case,
    get_list_packages_use_case,
    get_package_use_case,
    get_upload_package_use_case,
)
from .schemas import GetPackageResponse, ListPackagesResponse, UploadPackageResponse
from .usecases import (
    DownloadPackageUseCase,
    GetPackageUseCase,
    ListPackagesUseCase,
    UploadPackageUseCase,
)

# 에이전트 패키지 관리 API
router = APIRouter(tags=["Packages"])


@cbv(router)
class PackageAdminRouter:
    @router.api_route(
        "/download",
        methods=["GET", "HEAD"],
        dependencies=[Depends(check_download_token)],
    )
    async def download_package_by_version(
        self,
        version: str = "latest",
        download_use_case: DownloadPackageUseCase = Depends(
            get_download_package_use_case
        ),
    ):
        """에이전트 패키지를 토큰을 사용하여 버전별로 다운로드합니다. (Client Setup Template용)"""
        return await download_use_case.execute(version)

    @router.post(
        "/upload",
        response_model=UploadPackageResponse,
        dependencies=[Depends(admin_verify_guard)],
    )
    async def upload_package(
        self,
        file: UploadFile = File(...),
        upload_use_case: UploadPackageUseCase = Depends(get_upload_package_use_case),
    ):
        """에이전트 Zip 패키지를 업로드합니다. (운영자 전용)"""
        return await upload_use_case.execute(file)

    @router.get(
        "/",
        response_model=GetPackageResponse | ListPackagesResponse,
        dependencies=[Depends(get_current_identity)],
    )
    async def list_packages(
        self,
        version: str | None = None,
        get_package_use_case: GetPackageUseCase = Depends(get_package_use_case),
        list_use_case: ListPackagesUseCase = Depends(get_list_packages_use_case),
    ):
        """패키지 목록 또는 특정 버전을 조회합니다. (운영자 전용)"""
        if version:
            return await get_package_use_case.execute(version)
        return await list_use_case.execute()
