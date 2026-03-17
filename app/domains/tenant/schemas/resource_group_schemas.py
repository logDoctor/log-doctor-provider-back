from pydantic import BaseModel


class AzureResourceGroupResponse(BaseModel):
    """Azure 리소스 그룹 상세 응답 스펙"""

    id: str
    name: str
    location: str
