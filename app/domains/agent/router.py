from fastapi import Depends, Request
from fastapi_restful.cbv import cbv

from app.core.auth.guards import admin_verify_guard, get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import (
    get_check_azure_resource_group_status_use_case,
    get_confirm_agent_deletion_use_case,
    get_deactivate_agent_use_case,
    get_handshake_agent_use_case,
    get_platform_admin_list_agents_use_case,
    get_request_agent_update_use_case,
    get_tenant_user_list_agents_use_case,
)
from .schemas import (
    CheckAzureResourceGroupStatusResponse,
    ConfirmAgentDeletionResponse,
    DeactivateAgentResponse,
    HandshakeAgentRequest,
    HandshakeAgentResponse,
    PlatformAdminListAgentsResponse,
    RequestAgentUpdateRequest,
    RequestAgentUpdateResponse,
    TenantUserListAgentsResponse,
)
from .usecases import (
    CheckAzureResourceGroupStatusUseCase,
    ConfirmAgentDeletionUseCase,
    DeactivateAgentUseCase,
    HandshakeAgentUseCase,
    PlatformAdminListAgentsUseCase,
    RequestAgentUpdateUseCase,
    TenantUserListAgentsUseCase,
)

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
        tenant_id: str,
        request: RequestAgentUpdateRequest,
        admin_identity: Identity = Depends(admin_verify_guard),
        use_case: RequestAgentUpdateUseCase = Depends(
            get_request_agent_update_use_case
        ),
    ):
        """에이전트 패키지 업데이트를 요청합니다. (운영자 전용)"""
        return await use_case.execute(
            identity=admin_identity,
            tenant_id=tenant_id,
            agent_id=client_agent_id,
            target_version=request.target_version,
        )

    @router.post("/handshake", response_model=HandshakeAgentResponse)
    async def handshake(
        self,
        request: HandshakeAgentRequest,
        req: Request,
        use_case: HandshakeAgentUseCase = Depends(get_handshake_agent_use_case),
    ):
        """
        에이전트가 최초 실행되거나 재시작될 때 호출하여 자신의 정보를 등록/갱신합니다.
        """
        client_ip = req.client.host if req.client else "unknown"
        return await use_case.execute(request, client_ip)
