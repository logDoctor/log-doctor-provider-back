from pydantic import BaseModel, ConfigDict

from app.domains.agent.models import AgentStatus


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


class AgentCommandMessage(BaseModel):
    """Azure Queue를 통해 에이전트로 전달되는 명령 스펙"""

    agent_id: str
    trace_id: str | None = None
    command: str
    params: dict | None = None


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
    storage_account_name: str | None = None
    client_ip: str
    version: str
    capabilities: list[str] = []
    status: str
    analysis_schedule: str
    last_handshake_at: str


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


class AgentUpdateRequest(BaseModel):
    """에이전트 상태 및 설정 변경 요청 (PATCH)"""

    status: AgentStatus | None = None
    tenant_id: str


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


class TenantAdminUninstallResponse(BaseModel):
    success: bool
    action: str
    tenant_id: str | None = None
    results: list[dict] | None = None
