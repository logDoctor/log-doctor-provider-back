import re

from pydantic import BaseModel


class PackageInfo(BaseModel):
    """에이전트 패키지 정보를 나타내는 도메인 모델입니다."""

    filename: str
    size: int
    url: str
    version: str = "unknown"

    @staticmethod
    def parse_version(filename: str) -> str:
        """파일명에서 버전을 추출합니다. (예: agent-v1.1.0.zip → 1.1.0)"""
        match = re.search(r"agent-v(.+)\.zip$", filename)
        return match.group(1) if match else "unknown"
