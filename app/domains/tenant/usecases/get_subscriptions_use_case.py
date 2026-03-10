from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.exceptions import UnauthorizedException
from app.domains.tenant.repositories import SubscriptionRepository, TenantRepository
from app.domains.tenant.schemas import SubscriptionItem, SubscriptionListResponse


class GetSubscriptionsUseCase:
    """테넌트 사용자가 접근 가능한 Azure 구독 목록을 조회합니다."""

    def __init__(
        self, repository: SubscriptionRepository, tenant_repository: TenantRepository
    ):
        self.repository = repository
        self.tenant_repository = tenant_repository

    async def execute(self, identity: Identity) -> SubscriptionListResponse:
        tenant = await self.tenant_repository.get_by_id(identity.tenant_id)
        is_registered = tenant and tenant.registered_at

        if not is_registered:
            has_permission = identity.is_admin() or len(identity.roles) > 0
            if not has_permission:
                raise UnauthorizedException(
                    "ACCESS_DENIED|NOT_ASSIGNED|You do not have permission to use LogDoctor. "
                    "Please have your administrator assign an app role in 'Enterprise Applications'."
                )
            privileged_emails = []
        else:
            privileged_emails = [
                a["email"].lower()
                for a in (tenant.privileged_accounts or [])
                if "email" in a
            ]

        current_user_email = (identity.email or "").lower()

        if (
            is_registered
            and not identity.is_admin()
            and current_user_email not in privileged_emails
        ):
            display_emails = ", ".join(privileged_emails)
            raise UnauthorizedException(
                f"ACCESS_DENIED|NOT_ASSIGNED|Access denied. Please request permission from an operator. (Assigned operators: {display_emails})"
            )

        arm_token = await get_obo_access_token(identity.sso_token)
        raw_subscriptions = await self.repository.list_subscriptions(arm_token)

        subscriptions = [
            SubscriptionItem(
                subscription_id=sub["subscriptionId"],
                display_name=sub["displayName"],
            )
            for sub in raw_subscriptions
        ]

        return SubscriptionListResponse(subscriptions=subscriptions)
