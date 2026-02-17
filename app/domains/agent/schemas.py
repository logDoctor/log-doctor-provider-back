from pydantic import BaseModel


class AgentHandshakeRequest(BaseModel):
    tenant_id: str
    subscription_id: str
    agent_id: str
    agent_version: str = "1.0.0"


class AgentHandshakeResponse(BaseModel):
    success: bool
    message: str
