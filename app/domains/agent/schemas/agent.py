from pydantic import BaseModel, ConfigDict


class HandshakeAgentRequest(BaseModel):
    tenant_id: str
    subscription_id: str
    resource_group_name: str
    function_app_name: str
    location: str
    environment: str
    runtime_env: dict
    storage_account_name: str | None = None
    agent_id: str
    capabilities: list[str] = []
    agent_version: str


class HandshakeAgentResponse(BaseModel):
    message: str
    status: str | None = None


class AgentCommandMessage(BaseModel):
    """Azure Queue를 통해 에이전트로 전달되는 명령 스펙"""

    agent_id: str
    trace_id: str | None = None
    report_id: str | None = None
    command: str
    params: dict | None = None
    resource_groups: list[str] | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    subscription_id: str
    resource_group_name: str
    function_app_name: str
    location: str
    environment: str
    runtime_env: dict
    storage_account_name: str | None = None
    client_ip: str
    version: str
    capabilities: list[str] = []
    status: str
    analysis_schedule: str
    last_handshake_at: str
    teams_info: dict | None = None
    can_manage: bool = False


class UpdateAgentRequest(BaseModel):
    """에이전트 속성 업데이트 요청"""

    teams_info: dict | None = None
    status: str | None = None


class UpdateAgentResponse(BaseModel):
    """에이전트 속성 업데이트 응답"""

    message: str
    agent: AgentResponse


class PaginatedAgentResponse(BaseModel):
    """공통 페이징 응답 스펙"""

    items: list[AgentResponse]
    total_count: int
    skip: int
    limit: int


class PlatformAdminListAgentsResponse(PaginatedAgentResponse):
    pass


class TenantUserListAgentsResponse(PaginatedAgentResponse):
    pass


class DeactivateAgentResponse(BaseModel):
    message: str
    agent: AgentResponse


class ConfirmAgentDeletionResponse(BaseModel):
    message: str
    agent: AgentResponse


class CheckAzureResourceGroupStatusResponse(BaseModel):
    exists: bool
    resource_group_name: str


class RequestAgentUpdateRequest(BaseModel):
    """에이전트 OTA 업데이트 요청"""

    tenant_id: str
    target_version: str = "latest"


class RequestAgentUpdateResponse(BaseModel):
    """에이전트 OTA 업데이트 응답"""

    message: str
    agent: AgentResponse
    success: bool = True


class TenantAdminUninstallResponse(BaseModel):
    success: bool
    action: str
    tenant_id: str | None = None
    results: list[dict] | None = None


class DiscoveredAzureResource(BaseModel):
    storage_account_name: str
    resource_group: str
    location: str
    is_registered: bool
    resource_id: str
    created_at: str | None = None


class DiscoverAgentResourcesResponse(BaseModel):
    items: list[DiscoveredAzureResource]


class PokeAgentRequest(BaseModel):
    storage_account_name: str
    subscription_id: str


class PokeAgentResponse(BaseModel):
    success: bool
    message: str
