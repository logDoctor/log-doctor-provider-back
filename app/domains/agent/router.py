from fastapi import Depends, Request
from fastapi_restful.cbv import cbv

from app.core.auth.guards import admin_verify_guard, get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import (
    get_check_azure_resource_group_status_use_case,
    get_confirm_agent_deletion_use_case,
    get_create_schedule_use_case,
    get_deactivate_agent_use_case,
    get_delete_schedule_use_case,
    get_discover_agent_resources_use_case,
    get_handshake_agent_use_case,
    get_list_schedules_use_case,
    get_platform_admin_list_agents_use_case,
    get_poke_agent_use_case,
    get_report_agent_issue_use_case,
    get_request_agent_update_use_case,
    get_tenant_user_list_agents_use_case,
    get_trigger_scheduled_run_use_case,
    get_update_agent_use_case,
    get_update_schedule_use_case,
)
from .schemas import (
    CheckAzureResourceGroupStatusResponse,
    ConfirmAgentDeletionResponse,
    DeactivateAgentResponse,
    DiscoverAgentResourcesResponse,
    HandshakeAgentRequest,
    HandshakeAgentResponse,
    PlatformAdminListAgentsResponse,
    PokeAgentRequest,
    PokeAgentResponse,
    RequestAgentUpdateRequest,
    RequestAgentUpdateResponse,
    ScheduleListResponse,
    ScheduleResponse,
    TenantUserListAgentsResponse,
    TriggerScheduledRunResponse,
    UpdateAgentRequest,
    UpdateAgentResponse,
)
from .schemas.issue import AgentIssuesCreate
from .schemas.schedule import CreateScheduleRequest, UpdateScheduleRequest
from .usecases import (
    CheckAzureResourceGroupStatusUseCase,
    ConfirmAgentDeletionUseCase,
    CreateScheduleUseCase,
    DeactivateAgentUseCase,
    DeleteScheduleUseCase,
    DiscoverAgentResourcesUseCase,
    HandshakeAgentUseCase,
    ListSchedulesUseCase,
    PlatformAdminListAgentsUseCase,
    PokeAgentUseCase,
    RequestAgentUpdateUseCase,
    TenantUserListAgentsUseCase,
    TriggerScheduledRunUseCase,
    UpdateAgentUseCase,
    UpdateScheduleUseCase,
)
from .usecases.report_agent_issue import ReportAgentIssueUseCase

router = APIRouter(tags=["Agents"])


@cbv(router)
class AgentRouter:
    @router.get(
        "/",
        response_model=PlatformAdminListAgentsResponse | TenantUserListAgentsResponse,
    )
    async def list_agents(
        self,
        identity: Identity = Depends(get_current_identity),
        tenant_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
        tenant_user_list_agents_use_case: TenantUserListAgentsUseCase = Depends(
            get_tenant_user_list_agents_use_case
        ),
        platform_admin_list_agents_use_case: PlatformAdminListAgentsUseCase = Depends(
            get_platform_admin_list_agents_use_case
        ),
    ):
        """에이전트 목록을 조회합니다. (역할 기반: 어드민은 전체/필터링, 사용자는 본인 테넌트)"""
        if identity.is_platform_admin():
            return await platform_admin_list_agents_use_case.execute(
                identity=identity, tenant_id=tenant_id, skip=skip, limit=limit
            )

        return await tenant_user_list_agents_use_case.execute(
            identity=identity, tenant_id=tenant_id, skip=skip, limit=limit
        )

    @router.delete("/{client_agent_id}", response_model=DeactivateAgentResponse)
    async def delete_agent(
        self,
        client_agent_id: str,
        tenant_id: str,
        admin_identity: Identity = Depends(admin_verify_guard),
        deactivate_use_case: DeactivateAgentUseCase = Depends(
            get_deactivate_agent_use_case
        ),
    ):
        """
        에이전트 비활성화를 요청합니다. (운영자 전용)
        에이전트 상태를 DEACTIVATING으로 변경하고 Azure 리소스 삭제를 시작합니다.
        """
        return await deactivate_use_case.execute(
            identity=admin_identity,
            tenant_id=tenant_id,
            agent_id=client_agent_id,
        )

    @router.patch("/{client_agent_id}", response_model=UpdateAgentResponse)
    async def update_agent(
        self,
        client_agent_id: str,
        tenant_id: str,
        request: UpdateAgentRequest,
        admin_identity: Identity = Depends(admin_verify_guard),
        use_case: UpdateAgentUseCase = Depends(get_update_agent_use_case),
    ):
        """에이전트 속성을 업데이트합니다. (운영자 전용)"""
        return await use_case.execute(
            identity=admin_identity,
            tenant_id=tenant_id,
            agent_id=client_agent_id,
            status=request.status,
            teams_info=request.teams_info,
        )

    @router.post(
        "/{client_agent_id}/confirm-deletion",
        response_model=ConfirmAgentDeletionResponse,
    )
    async def confirm_agent_deletion(
        self,
        client_agent_id: str,
        tenant_id: str,
        admin_identity: Identity = Depends(admin_verify_guard),
        confirm_deletion_use_case: ConfirmAgentDeletionUseCase = Depends(
            get_confirm_agent_deletion_use_case
        ),
    ):
        """
        에이전트 삭제를 확정합니다. (운영자 전용)
        Azure 리소스 삭제가 완료된 후 호출하여 DB 상태를 DELETED로 변경합니다.
        """
        return await confirm_deletion_use_case.execute(
            tenant_id=tenant_id,
            agent_id=client_agent_id,
        )

    @router.get(
        "/{client_agent_id}/resource-group",
        response_model=CheckAzureResourceGroupStatusResponse,
    )
    async def check_azure_resource_group_status(
        self,
        client_agent_id: str,
        tenant_id: str,
        admin_identity: Identity = Depends(admin_verify_guard),
        use_case: CheckAzureResourceGroupStatusUseCase = Depends(
            get_check_azure_resource_group_status_use_case
        ),
    ):
        """에이전트의 실제 Azure 리소스 존재 여부를 확인합니다. (운영자 전용)"""
        return await use_case.execute(
            identity=admin_identity,
            tenant_id=tenant_id,
            agent_id=client_agent_id,
        )

    @router.post(
        "/{client_agent_id}/request-update", response_model=RequestAgentUpdateResponse
    )
    async def request_update(
        self,
        client_agent_id: str,
        request: RequestAgentUpdateRequest,
        admin_identity: Identity = Depends(admin_verify_guard),
        use_case: RequestAgentUpdateUseCase = Depends(
            get_request_agent_update_use_case
        ),
    ):
        """에이전트 패키지 업데이트를 요청합니다. (운영자 전용)"""
        return await use_case.execute(
            identity=admin_identity,
            tenant_id=request.tenant_id,
            agent_id=client_agent_id,
            target_version=request.target_version,
        )

    @router.put("/handshake", response_model=HandshakeAgentResponse)
    async def handshake(
        self,
        request: HandshakeAgentRequest,
        req: Request,
        use_case: HandshakeAgentUseCase = Depends(get_handshake_agent_use_case),
    ):
        """에이전트가 최초 실행되거나 재시작될 때 호출하여 자신의 정보를 등록/갱신합니다."""
        client_ip = req.client.host if req.client else "unknown"
        return await use_case.execute(request, client_ip)

    @router.get("/azure-resources", response_model=DiscoverAgentResourcesResponse)
    async def discover_agent_resources(
        self,
        subscription_id: str,
        identity: Identity = Depends(get_current_identity),
        use_case: DiscoverAgentResourcesUseCase = Depends(
            get_discover_agent_resources_use_case
        ),
    ):
        """Azure 구독 내에서 에이전트로 등록 가능한 리소스를 탐색합니다."""
        # sso_token은 identity에서 가져옴 (있는 경우)
        sso_token = identity.sso_token if identity else ""
        tenant_id = identity.tenant_id if identity else ""

        resources = await use_case.execute(
            sso_token=sso_token, subscription_id=subscription_id, tenant_id=tenant_id
        )
        return DiscoverAgentResourcesResponse(items=resources)

    @router.post("/azure-resources/poke", response_model=PokeAgentResponse)
    async def poke_agent(
        self,
        request: PokeAgentRequest,
        identity: Identity = Depends(get_current_identity),
        use_case: PokeAgentUseCase = Depends(get_poke_agent_use_case),
    ):
        """특정 에이전트 리소스에 Wake-up 신호를 전송합니다."""
        success = await use_case.execute(
            storage_account_name=request.storage_account_name,
            subscription_id=request.subscription_id,
        )
        return PokeAgentResponse(
            success=success,
            message="Poke signal sent" if success else "Failed to send poke signal",
        )


@router.post(
    "/{agent_id}/trigger-scheduled-run", response_model=TriggerScheduledRunResponse
)
async def trigger_scheduled_run(
    agent_id: str,
    tenant_id: str,
    use_case: TriggerScheduledRunUseCase = Depends(get_trigger_scheduled_run_use_case),
):
    """
    에이전트 타이머가 30분마다 호출하여 실행 시각이 된 정기 검진을 트리거합니다.
    실행 시각이 된 스케줄이 있으면 Report를 생성하고 진단 큐에 메시지를 push합니다.
    """
    return await use_case.execute(tenant_id=tenant_id, agent_id=agent_id)


@router.post("/{agent_id}/issues", status_code=201)
async def report_agent_issue(
    agent_id: str,
    request: AgentIssuesCreate,
    tenant_id: str = "default_tenant",
    use_case: ReportAgentIssueUseCase = Depends(get_report_agent_issue_use_case),
):
    issues = await use_case.execute(
        tenant_id=tenant_id, agent_id=agent_id, request=request.items
    )
    return {
        "message": "Issues reported successfully",
        "count": len(issues),
        "ids": [issue.id for issue in issues],
    }


# --- Schedule sub-resource routes ---


@router.get("/{agent_id}/schedules", response_model=ScheduleListResponse)
async def list_schedules(
    agent_id: str,
    admin_identity: Identity = Depends(admin_verify_guard),
    use_case: ListSchedulesUseCase = Depends(get_list_schedules_use_case),
):
    """에이전트에 등록된 정기 검진 스케줄 목록을 조회합니다. (운영자 전용)"""
    schedules = await use_case.execute(identity=admin_identity, agent_id=agent_id)
    return ScheduleListResponse(items=schedules)


@router.post("/{agent_id}/schedules", response_model=ScheduleResponse, status_code=201)
async def create_schedule(
    agent_id: str,
    request: CreateScheduleRequest,
    admin_identity: Identity = Depends(admin_verify_guard),
    use_case: CreateScheduleUseCase = Depends(get_create_schedule_use_case),
):
    """에이전트에 정기 검진 스케줄을 추가합니다. (운영자 전용)"""
    return await use_case.execute(
        identity=admin_identity, agent_id=agent_id, request=request
    )


@router.patch("/{agent_id}/schedules/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    agent_id: str,
    schedule_id: str,
    request: UpdateScheduleRequest,
    admin_identity: Identity = Depends(admin_verify_guard),
    use_case: UpdateScheduleUseCase = Depends(get_update_schedule_use_case),
):
    """정기 검진 스케줄을 수정합니다. (운영자 전용)"""
    return await use_case.execute(
        identity=admin_identity,
        agent_id=agent_id,
        schedule_id=schedule_id,
        request=request,
    )


@router.delete("/{agent_id}/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    agent_id: str,
    schedule_id: str,
    admin_identity: Identity = Depends(admin_verify_guard),
    use_case: DeleteScheduleUseCase = Depends(get_delete_schedule_use_case),
):
    """정기 검진 스케줄을 삭제합니다. (운영자 전용)"""
    await use_case.execute(
        identity=admin_identity,
        agent_id=agent_id,
        schedule_id=schedule_id,
    )
