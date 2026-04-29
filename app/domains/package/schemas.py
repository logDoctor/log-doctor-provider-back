from pydantic import BaseModel

from .models import PackageInfo


class UploadPackageResponse(BaseModel):
    message: str
    package: PackageInfo


class ListPackagesResponse(BaseModel):
    items: list[PackageInfo]


class GetPackageResponse(PackageInfo):
    """PackageInfo를 그대로 상속하며 유즈케이스 명칭에 따른 명시성을 위해 사용"""

    pass


class GenerateUploadUrlResponse(BaseModel):
    url: str
    filename: str
    method: str = "PUT"
    headers: dict[str, str] = {"x-ms-blob-type": "BlockBlob"}
