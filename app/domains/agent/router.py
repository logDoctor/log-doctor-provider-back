from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from fastapi_restful.cbv import cbv

from app.core.auth.guards import check_admin, check_tenant, get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import (
    get_check_azure_status_use_case,
    get_confirm_agent_deletion_use_case,
    get_deactivate_agent_use_case,
    get_handshake_agent_use_case,
    get_list_agents_use_case,
    get_should_agent_run_use_case,
    get_trigger_agent_analysis_use_case,
    get_update_agent_use_case,
)
from .schemas import (
    AgentDeactivateResponse,
    AgentHandshakeRequest,
    AgentHandshakeResponse,
    AgentPollingResponse,
    AgentResponse,
    AgentTriggerRequest,
    AgentTriggerResponse,
    AgentUpdateRequest,
    AgentUpdateResponse,
    AzureStatusResponse,
    ConfirmDeletionResponse,
    PaginatedAgentResponse,
)
from .usecases import (
    CheckAzureStatusUseCase,
    ConfirmAgentDeletionUseCase,
    DeactivateAgentUseCase,
    HandshakeAgentUseCase,
    ListAgentsUseCase,
    ShouldAgentRunUseCase,
    TriggerAgentAnalysisUseCase,
    UpdateAgentUseCase,
)

router = APIRouter(prefix="/agents", tags=["Agent"])


@cbv(router)
class AgentRouter:
    def __init__(
        self,
        handshake_use_case: HandshakeAgentUseCase = Depends(get_handshake_agent_use_case),
        list_use_case: ListAgentsUseCase = Depends(get_list_agents_use_case),
        should_run_use_case: ShouldAgentRunUseCase = Depends(get_should_agent_run_use_case),
        trigger_use_case: TriggerAgentAnalysisUseCase = Depends(get_trigger_agent_analysis_use_case),
        update_use_case: UpdateAgentUseCase = Depends(get_update_agent_use_case),
        deactivate_use_case: DeactivateAgentUseCase = Depends(get_deactivate_agent_use_case),
        check_azure_status_use_case: CheckAzureStatusUseCase = Depends(get_check_azure_status_use_case),
        confirm_deletion_use_case: ConfirmAgentDeletionUseCase = Depends(get_confirm_agent_deletion_use_case),
    ):
        self.handshake_use_case = handshake_use_case
        self.list_use_case = list_use_case
        self.should_run_use_case = should_run_use_case
        self.trigger_use_case = trigger_use_case
        self.update_use_case = update_use_case
        self.deactivate_use_case = deactivate_use_case
        self.check_azure_status_use_case = check_azure_status_use_case
        self.confirm_deletion_use_case = confirm_deletion_use_case

    @router.get("/", response_model=PaginatedAgentResponse)
    async def list_agents(
        self,
        identity: Identity = Depends(get_current_identity),
        tenant_id: str | None = None,
        skip: int = 0,
        limit: int = 10,
    ):
        """
        에이전트 목록을 조회합니다.
        (운영자는 전체 또는 특정 테넌트, 일반 사용자는 자신의 테넌트 정보만 접근 가능)
        """
        items, total_count = await self.list_use_case.execute(
            identity, tenant_id=tenant_id, skip=skip, limit=limit
        )
        return PaginatedAgentResponse(
            items=[AgentResponse.model_validate(item) for item in items],
            total_count=total_count,
            skip=skip,
            limit=limit
        )

    @router.post("/handshake", response_model=AgentHandshakeResponse)
    async def request_handshake(
        self,
        fastapi_req: Request,
        request: AgentHandshakeRequest,
        identity: Identity = Depends(get_current_identity),
        tenant_id: str = Depends(check_tenant),
    ):
        """
        에이전트로부터의 최초 핸드쉐이크 요청을 처리하고 정보를 등록합니다.
        (Decorator-based Tenant Validation 적용)
        """
        client_ip = fastapi_req.client.host if fastapi_req.client else ""
        return await self.handshake_use_case.execute(request, client_ip=client_ip)

    @router.get("/{client_agent_id}/polling", response_model=AgentPollingResponse)
    async def polling_status(
        self,
        client_agent_id: str,
        identity: Identity = Depends(get_current_identity),
        tenant_id: str = Depends(check_tenant),
    ):
        """
        에이전트가 주기적으로 호출하여 분석을 수행해야 하는지 확인합니다. (Polling)
        """
        return await self.should_run_use_case.execute(tenant_id, client_agent_id)

    @router.post("/trigger", response_model=AgentTriggerResponse)
    async def trigger(
        self,
        request: AgentTriggerRequest = None,
        identity: Identity = Depends(get_current_identity),
        is_admin: bool = Depends(check_admin),
    ):
        """
        사용자의 요청에 의해 특정 에이전트의 분석을 즉시 트리거합니다. (운영자 전용)
        """
        return await self.trigger_use_case.execute(request)

    @router.put("/{client_agent_id}", response_model=AgentUpdateResponse)
    async def update_agent(
        self,
        client_agent_id: str,
        request: AgentUpdateRequest,
        identity: Identity = Depends(get_current_identity),
        is_admin: bool = Depends(check_admin),
    ):
        """
        특정 에이전트의 정보(스케줄, 상태 등)를 변경합니다. (운영자 전용)
        """
        # 경로의 agent_id를 요청 데이터에 맞춤
        return await self.update_use_case.execute(request)

    @router.delete("/{client_agent_id}", response_model=AgentDeactivateResponse)
    async def deactivate_agent(
        self,
        client_agent_id: str,
        tenant_id: str,
        delete_azure_resources: bool = True,
        identity: Identity = Depends(get_current_identity),
        is_admin: bool = Depends(check_admin),
    ):
        """
        에이전트를 비활성화합니다. (운영자 전용)
        Azure 리소스 그룹 삭제 요청을 보내고 DEACTIVATING 상태로 전환합니다.
        """
        result = await self.deactivate_use_case.execute(
            identity=identity,
            tenant_id=tenant_id,
            agent_id=client_agent_id,
            delete_azure_resources=delete_azure_resources,
        )
        status_code = 202 if result["success"] else 500
        return JSONResponse(content=result, status_code=status_code)

    @router.get("/{client_agent_id}/azure-status", response_model=AzureStatusResponse)
    async def check_azure_status(
        self,
        client_agent_id: str,
        tenant_id: str,
        identity: Identity = Depends(get_current_identity),
        is_admin: bool = Depends(check_admin),
    ):
        """
        에이전트의 Azure 리소스 그룹 존재 여부를 확인합니다. (순수 읽기, 운영자 전용)
        Managed Identity를 사용합니다.
        """
        return await self.check_azure_status_use_case.execute(
            identity=identity,
            tenant_id=tenant_id,
            agent_id=client_agent_id,
        )

    @router.post("/{client_agent_id}/confirm-deletion", response_model=ConfirmDeletionResponse)
    async def confirm_deletion(
        self,
        client_agent_id: str,
        tenant_id: str,
        identity: Identity = Depends(get_current_identity),
        is_admin: bool = Depends(check_admin),
    ):
        """
        Azure 리소스 삭제 확인 후 에이전트를 최종 DELETED 상태로 전환합니다. (운영자 전용)
        """
        return await self.confirm_deletion_use_case.execute(
            tenant_id=tenant_id,
            agent_id=client_agent_id,
        )

