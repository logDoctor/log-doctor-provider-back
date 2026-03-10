from app.core.exceptions import InternalServerException, NotFoundException
from app.domains.agent.models import Agent
from app.domains.agent.repository import AgentRepository
from app.domains.agent.schemas import HandshakeAgentRequest, HandshakeAgentResponse
from app.domains.tenant.repository import TenantRepository


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

        # 이미 활성 상태이고 버전이 같다면, 갱신이 필요 없는 것으로 보일 수 있으나
        # 런타임 정보나 IP가 변경되었을 수 있으므로 항상 업데이트 로직을 타도록 합니다.
        # 단, 삭제된 상태인 경우에는 무시하고 새로 생성합니다.

        # 만약 에이전트가 존재하지만 이미 삭제(DELETED) 상태라면,
        # 과거 이력을 보전하기 위해 기존 엔터티를 무시하고 새로 생성합니다.
        if agent and agent.is_deleted():
            agent = None

        if agent:
            agent.activate()

            agent.update_version(request.agent_version)
            # Update all mutable metadata from the handshake
            agent.resource_group_name = request.resource_group_name
            agent.function_app_name = request.function_app_name
            agent.location = request.location
            agent.environment = request.environment
            agent.runtime_env = request.runtime_env
            agent.storage_account_name = request.storage_account_name
            agent.capabilities = request.capabilities  # 에이전트 기능 목록 동기화
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

        result = await self.repository.upsert_agent(agent.to_dict())
        if not result:
            raise InternalServerException("Failed to persist agent handshake")

        return HandshakeAgentResponse(
            message=f"Agent {result.agent_id} (v{result.version}) handshaked successfully (Status: {result.status})",
        )
