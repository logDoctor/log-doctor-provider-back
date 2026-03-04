from pydantic import BaseModel, ConfigDict


class AgentHandshakeRequest(BaseModel):
    tenant_id: str
    subscription_id: str
    resource_group_name: str
    function_app_name: str
    location: str
    environment: str
    runtime_env: dict
    agent_id: str
    capabilities: list[str] = []  # 에이전트가 수행 가능한 기능 목록 (예: detect, filter)
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


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    agent_id: str
    tenant_id: str
    subscription_id: str
    resource_group_name: str
    function_app_name: str
    location: str
    environment: str
    runtime_env: dict
    client_ip: str
    version: str
    capabilities: list[str] = []  # 에이전트 기능 목록
    status: str
    analysis_schedule: str
    last_handshake_at: str


class PaginatedAgentResponse(BaseModel):
    items: list[AgentResponse]
    total_count: int
    skip: int
    limit: int


class AgentDeactivateResponse(BaseModel):
    success: bool
    message: str
    azure_status: str  # 'ACCEPTED', 'NOT_FOUND', 'FAILED'


class AzureStatusResponse(BaseModel):
    exists: bool
    resource_group_name: str


class ConfirmDeletionResponse(BaseModel):
    confirmed: bool
    message: str


class AgentUpdateDeployRequest(BaseModel):
    """에이전트 OTA 업데이트 요청"""
    tenant_id: str
    target_version: str = "latest"


class AgentUpdateDeployResponse(BaseModel):
    """에이전트 OTA 업데이트 응답"""
    success: bool
    message: str
    current_version: str
    target_version: str
    arm_status: str | None = None

