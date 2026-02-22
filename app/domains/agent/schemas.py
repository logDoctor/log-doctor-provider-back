from pydantic import BaseModel, Field


# 1. 에이전트가 우리에게 보낼 데이터 (요청)
class AgentHandshakeRequest(BaseModel):
    tenant_id: str = Field(..., description="고객사 Tenant ID")
    subscription_id: str = Field(..., description="고객사 Azure 구독 ID")
    agent_id: str = Field(..., description="배포된 에이전트의 고유 ID")
    agent_version: str = Field(..., description="에이전트 버전 (예: 1.0.0)")
    hostname: str = Field(..., description="에이전트 호스트명")


# 2. 우리가 에이전트에게 돌려줄 데이터 (응답)
class AgentHandshakeResponse(BaseModel):
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="결과 메시지")
