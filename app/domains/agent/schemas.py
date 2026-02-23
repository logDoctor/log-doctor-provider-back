from pydantic import BaseModel


class AgentHandshakeRequest(BaseModel):
    tenant_id: str
    subscription_id: str
    agent_id: str
    agent_version: str = "1.0.0"


class AgentHandshakeResponse(BaseModel):
    success: bool
    message: str


class AgentPollingResponse(BaseModel):
    should_run: bool
    command: str | None = None
    params: dict | None = None


class AgentTriggerRequest(BaseModel):
    tenant_id: str
    agent_id: str
    params: dict | None = None


class AgentTriggerResponse(BaseModel):
    success: bool
    message: str


class AgentUpdateRequest(BaseModel):
    tenant_id: str
    agent_id: str
    version: str | None = None
    status: str | None = None
    analysis_schedule: str | None = None


class AgentUpdateResponse(BaseModel):
    success: bool
    message: str
    updated_fields: list[str]
