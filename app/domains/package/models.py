from pydantic import BaseModel


class PackageInfo(BaseModel):
    """에이전트 패키지 정보를 나타내는 도메인 모델입니다."""

    filename: str
    size: int
    url: str
