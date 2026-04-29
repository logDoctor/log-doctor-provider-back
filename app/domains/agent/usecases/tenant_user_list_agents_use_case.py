import asyncio

from app.core.auth import Identity, get_obo_access_token
from app.core.exceptions import ForbiddenException
from app.core.interfaces.azure_arm import AzureArmService
from app.domains.agent.repositories import AgentRepository
from app.domains.agent.schemas import AgentResponse, TenantUserListAgentsResponse
from app.domains.tenant.repositories import SubscriptionRepository, TenantRepository


# TODO: 리팩토링 필요
class TenantUserListAgentsUseCase:
    """테넌트 사용자용 에이전트 목록 조회 유스케이스.

    본인이 속한 테넌트의 에이전트 중, Azure RBAC 권한이 있는 구독의 에이전트만 조회할 수 있습니다.
    """

    def __init__(
        self,
        agent_repository: AgentRepository,
        subscription_repository: SubscriptionRepository,
        tenant_repository: TenantRepository,
        azure_arm_service: AzureArmService,
    ):
        self.agent_repository = agent_repository
        self.subscription_repository = subscription_repository
        self.tenant_repository = tenant_repository
        self.azure_arm_service = azure_arm_service

    async def execute(
        self,
        identity: Identity,
        tenant_id: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> TenantUserListAgentsResponse:
        """본인 테넌트의 에이전트 목록을 조회합니다 (구독 권한 기반 필터링 포함)."""

        if tenant_id and tenant_id != identity.tenant_id:
            raise ForbiddenException(
                "You do not have permission to access other tenant's information."
            )

        target_tid = identity.tenant_id

        try:
            allowed_sub_ids = await self._get_allowed_subscription_ids(identity)
        except Exception:
            return TenantUserListAgentsResponse(
                items=[], total_count=0, skip=skip, limit=limit
            )
        if not allowed_sub_ids:
            return TenantUserListAgentsResponse(
                items=[], total_count=0, skip=skip, limit=limit
            )

        items, total = await self.agent_repository.list_agents(
            target_tid, subscription_ids=allowed_sub_ids, skip=skip, limit=limit
        )

        unique_subs = list({a.subscription_id for a in items if getattr(a, "subscription_id", None)})
        sub_permissions = {}

        async def check_perm(sub_id: str):
            try:
                await self.azure_arm_service.check_deployment_permission(identity.sso_token, sub_id)
                return sub_id, True
            except Exception:
                return sub_id, False

        if unique_subs:
            results = await asyncio.gather(*(check_perm(sub) for sub in unique_subs))
            sub_permissions = dict(results)

        response_items = []
        for a in items:
            resp = AgentResponse.model_validate(a)
            resp.can_manage = sub_permissions.get(resp.subscription_id, False)
            response_items.append(resp)

        return TenantUserListAgentsResponse(
            items=response_items,
            total_count=total,
            skip=skip,
            limit=limit,
        )

    async def _get_allowed_subscription_ids(self, identity: Identity) -> list[str]:
        """현재 사용자가 볼 수 있는 구독 ID 목록을 추출합니다."""
        tenant = await self.tenant_repository.get_by_id(identity.tenant_id)
        if not tenant or not tenant.registered_at:
            # 미등록 테넌트인 경우 관리자나 역할 보유자만 허용
            if not identity.is_privileged():
                return []
        else:
            # 등록된 테넌트인 경우 운영자 리스트 체크
            privileged_emails = [
                a["email"].lower()
                for a in (tenant.privileged_accounts or [])
                if "email" in a
            ]
            current_user_email = (identity.email or "").lower()
            if not identity.is_privileged() and current_user_email not in privileged_emails:
                return []

        # OBO 토큰을 통한 Azure 구독 목록 조회
        try:
            arm_token = await get_obo_access_token(identity.sso_token)
            raw_subs = await self.subscription_repository.list_subscriptions(arm_token)
            return [s["subscriptionId"] for s in raw_subs]
        except Exception:
            return []
