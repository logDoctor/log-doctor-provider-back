import logging

from app.core.exceptions import InternalServerException, NotFoundException
from app.domains.agent.models import Agent, AgentStatus
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.schemas import HandshakeAgentRequest, HandshakeAgentResponse
from app.domains.tenant.repositories import TenantRepository


class HandshakeAgentUseCase:
    def __init__(
        self, repository: AgentRepository, tenant_repository: TenantRepository
    ):
        self.repository = repository
        self.tenant_repository = tenant_repository

    async def execute(
        self, request: HandshakeAgentRequest, client_ip: str
    ) -> HandshakeAgentResponse:
        tenant = await self.tenant_repository.get_by_id(request.tenant_id)
        if tenant is None:
            raise NotFoundException(f"Tenant {request.tenant_id} not found")

        agent = await self.repository.get_active_agent_by_client_id(
            tenant_id=request.tenant_id, agent_id=request.agent_id
        )

        # 1. 삭제된 에이전트인 경우 좀비 방지
        # 이미 삭제 완료(DELETED)되었거나 삭제 중(DEACTIVATING)인 에이전트가 보낸 핸드쉐이크는 무시합니다.
        # (Azure 리소스가 삭제되기 전까지 에이전트가 살아있을 수 있으므로 자연스러운 상황입니다.)
        if agent and (agent.is_deleted() or agent.is_deactivating()):
            return HandshakeAgentResponse(
                message=f"Handshake ignored: Agent {request.agent_id} is in {agent.status.value} state.",
                status=agent.status.value,
            )

        if agent:
            # 2. 업데이트 중인 경우의 특별 처리
            if agent.status == AgentStatus.UPDATING:
                if request.agent_version != agent.version:
                    # 새로운 버전으로 핸드쉐이크가 오면 업데이트 완료로 간주하고 활성화
                    logging.info(
                        f"Agent {agent.agent_id} updated from {agent.version} to {request.agent_version}. Activating."
                    )
                    agent.activate()
                    agent.update_version(request.agent_version)
                else:
                    # 여전히 구 버전이라면 업데이트가 진행 중인 것으로 보고 ACTIVE 전환을 유보함
                    # (이 상태에서 클라이언트는 아래 응답의 status를 보고 실행을 중단하게 됨)
                    logging.info(
                        f"Agent {agent.agent_id} is still on old version {agent.version} during update. Keeping UPDATING status."
                    )
            else:
                # 일반적인 경우(INITIALIZING 등) 활성화 및 버전 업데이트
                agent.activate()
                agent.update_version(request.agent_version)

            # 나머지 메타데이터는 항상 최신화
            agent.resource_group_name = request.resource_group_name
            agent.function_app_name = request.function_app_name
            agent.location = request.location
            agent.environment = request.environment
            agent.runtime_env = request.runtime_env
            agent.storage_account_name = request.storage_account_name
            agent.capabilities = request.capabilities
            agent.client_ip = client_ip
        else:
            agent = Agent.create(
                tenant_id=request.tenant_id,
                subscription_id=request.subscription_id,
                resource_group_name=request.resource_group_name,
                function_app_name=request.function_app_name,
                location=request.location,
                environment=request.environment,
                runtime_env=request.runtime_env,
                storage_account_name=request.storage_account_name,
                client_ip=client_ip,
                agent_id=request.agent_id,
                version=request.agent_version,
                capabilities=request.capabilities,
            )

        result = await self.repository.upsert_agent(agent)
        if not result:
            raise InternalServerException("Failed to persist agent handshake")

        return HandshakeAgentResponse(
            message=f"Agent {result.agent_id} (v{result.version}) handshaked successfully (Status: {result.status.value})",
            status=result.status.value,
        )
