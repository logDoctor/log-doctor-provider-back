import logging
from app.core.auth import get_obo_access_token
from app.core.auth.models import Identity
from app.core.auth.services.graph_service import GraphService
from app.core.interfaces.azure_arm import AzureArmService

from ..repositories import TenantRepository

logger = logging.getLogger(__name__)


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

    async def execute(self, identity: Identity, subscription_id: str, emails: list[str] | None = None) -> list[dict]:
        """
        제공된 이메일 목록(`emails`) 또는 저장된 운영자 목록(`privileged_accounts`)에 대해
        Azure 구독에서 Owner/Contributor 권한 보유 여부를 조회합니다.
        """
        # 1. 대상 이메일 리스트 결정 (입력받은 emails 우선, 없으면 DB 조회)
        target_emails = emails if emails is not None else []
        
        if not target_emails:
            tenant = await self.tenant_repository.get_by_id(identity.tenant_id)
            if tenant:
                privileged_accounts = tenant.privileged_accounts or []
                target_emails = [
                    a.get("email") if isinstance(a, dict) else getattr(a, "email", "")
                    for a in privileged_accounts
                ]
                target_emails = [e for e in target_emails if e]

        # 현재 호출자(GA)는 무조건 포함시켜서 권한 확인
        if identity.email and identity.email not in target_emails:
            target_emails.append(identity.email)

        if not target_emails:
            return []

        # 2. 앱에 등록된 운영자 이메일 ➡ PrincipalId(GUID)로 사전 해독
        resolved_users = await self.graph_service.resolve_user_ids(
            identity.tenant_id, target_emails, sso_token=identity.sso_token
        )
        guid_to_email = {
            u["user_id"]: u["email"] for u in resolved_users if "user_id" in u
        }

        if not guid_to_email:
            logger.warning(f"Failed to resolve any user IDs for emails: {target_emails}")
            return []

        logger.info(f"Resolved users for permission check: {guid_to_email}")

        # 2. Azure 구독의 Role Assignments (역할 할당) 조회
        arm_token = await get_obo_access_token(identity.sso_token)
        assignments = await self.azure_arm_service.list_role_assignments(
            arm_token, subscription_id
        )

        # 🎯 Azure 공식 RoleDefinitionId 스니펫
        owner_role = "8e3af657-a8ff-443c-a75c-2fe8c4bcb635"
        contributor_role = "b24988ac-6180-42a0-ab88-20f7382dd24c"
        # User Access Administrator OR Role Based Access Control Administrator
        # 사용자 환경별 다양한 변종 ID 및 표준 ID 통합 관리
        uaa_roles = {
            "18d7d88d-d35e-4fb5-a5c3-7773c20a72d9",   # 사용자 환경용 UAA
            "f58310d9-a9f6-439a-9e8d-f62e7b41a168",   # 사용자 환경용 RBAC Admin
            "18d7d88d-d35e-455e-9961-a1c206a2e99b",   # 표준 UAA
            "f5881140-cc20-4f3a-8302-8f3713963430"    # 표준 RBAC Admin
        }

        # 사용자별 역활 목록 수집 (Aggregation)
        user_roles = {}  # { principal_id: set([role_id, ...]) }
        for assign in assignments:
            props = assign.get("properties", {})
            principal_id = props.get("principalId")
            role_def_id = props.get("roleDefinitionId", "").lower().split("/")[-1] # GUID만 추출

            # Principal ID 비교 시 대소문자 무시 (Graph vs ARM 간 차이 대응)
            principal_id_lower = principal_id.lower() if principal_id else ""
            
            # guid_to_email의 키값도 모두 소문자로 변환하여 비교
            target_guid_map = {k.lower(): v for k, v in guid_to_email.items()}

            if principal_id_lower in target_guid_map:
                if principal_id_lower not in user_roles:
                    user_roles[principal_id_lower] = set()
                user_roles[principal_id_lower].add(role_def_id)
                logger.info(f"Found role for {target_guid_map[principal_id_lower]}: {role_def_id}")

        # 3. 전역 관리자(Global Administrator) 여부 일괄 체크
        all_guids = list(guid_to_email.keys())
        global_admin_guids = await self.graph_service.check_global_admins(
            identity.tenant_id, all_guids, sso_token=identity.sso_token
        )

        all_admins = []
        for email in target_emails:
            # 이메일 기반으로 GUID 찾기 (대소문자 무시)
            email_lower = email.lower()
            guid = None
            for g, e in guid_to_email.items():
                if e.lower() == email_lower:
                    guid = g.lower()
                    break
            
            roles = user_roles.get(guid, set()) if guid else set()

            is_global_admin = guid in global_admin_guids if guid else False
            is_owner = owner_role in roles
            is_contributor = contributor_role in roles
            is_uaa = any(r in roles for r in uaa_roles)

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
