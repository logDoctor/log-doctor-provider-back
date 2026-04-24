from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.auth.services.graph_service import GraphService
from app.core.interfaces.azure_arm import AzureArmService

from ..repositories import TenantRepository


class ListSubscriptionAdministratorsUseCase:
    def __init__(
        self,
        tenant_repository: TenantRepository,
        graph_service: GraphService,
        azure_arm_service: AzureArmService,
    ):
        self.tenant_repository = tenant_repository
        self.graph_service = graph_service
        self.azure_arm_service = azure_arm_service

    async def execute(self, identity: Identity, subscription_id: str) -> list[dict]:
        """
        사용자가 지정한 운영자 목록(`privileged_accounts`) 중,
        Azure 구독에서 Owner/Contributor 권한을 동시 보유한 인원만 선별해 리턴합니다.
        """
        tenant = await self.tenant_repository.get_by_id(identity.tenant_id)
        if not tenant:
            return []

        privileged_accounts = tenant.privileged_accounts or []
        emails = [
            a.get("email") if isinstance(a, dict) else getattr(a, "email", "")
            for a in privileged_accounts
        ]
        emails = [e for e in emails if e]

        if not emails:
            return []

        # 1. 앱에 등록된 운영자 이메일 ➡ PrincipalId(GUID)로 사전 해독
        resolved_users = await self.graph_service.resolve_user_ids(
            identity.tenant_id, emails, sso_token=identity.sso_token
        )
        guid_to_email = {
            u["user_id"]: u["email"] for u in resolved_users if "user_id" in u
        }

        if not guid_to_email:
            return []

        # 2. Azure 구독의 Role Assignments (역할 할당) 조회
        arm_token = await get_obo_access_token(identity.sso_token)
        assignments = await self.azure_arm_service.list_role_assignments(
            arm_token, subscription_id
        )

        # 🎯 Azure 공식 RoleDefinitionId 스니펫
        owner_role = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
        contributor_role = "b24988ac-6180-42a0-ab88-20f7382dd24c"
        uaa_role = "18d7d88d-d35e-455e-9961-a1c206a2e99b"  # User Access Administrator

        # 사용자별 역활 목록 수집 (Aggregation)
        user_roles = {}  # { principal_id: set([role_id, ...]) }
        for assign in assignments:
            props = assign.get("properties", {})
            principal_id = props.get("principalId")
            role_def_id = props.get("roleDefinitionId", "").lower().split("/")[-1] # GUID만 추출

            if principal_id in guid_to_email:
                if principal_id not in user_roles:
                    user_roles[principal_id] = set()
                user_roles[principal_id].add(role_def_id)

        email_to_guid = {v: k for k, v in guid_to_email.items()}

        # 3. 전역 관리자(Global Administrator) 여부 일괄 체크
        all_guids = list(guid_to_email.keys())
        global_admin_guids = await self.graph_service.check_global_admins(
            identity.tenant_id, all_guids, sso_token=identity.sso_token
        )

        all_admins = []
        for email in emails:
            guid = email_to_guid.get(email)
            roles = user_roles.get(guid, set()) if guid else set()

            is_global_admin = guid in global_admin_guids if guid else False
            is_owner = owner_role in roles
            is_contributor = contributor_role in roles
            is_uaa = uaa_role in roles

            all_admins.append(
                {
                    "email": email,
                    "is_global_admin": is_global_admin,
                    "is_owner": is_owner,
                    "is_contributor": is_contributor,
                    "is_uaa": is_uaa,
                    "principal_id": guid,
                }
            )

        return all_admins
