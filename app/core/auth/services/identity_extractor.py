from ..models import Identity, IdentityType
from .jwt_service import JwtService


class IdentityExtractor:
    """헤더 정보를 바탕으로 호출자의 신원을 추출하는 전담 클래스"""

    def __init__(self, jwt_service: JwtService):
        self.jwt_service = jwt_service

    def extract(self, auth_header: str | None) -> Identity:
        """
        헤더 정보를 바탕으로 호출자의 신원을 추출합니다.
        """
        # 1. Bearer 토큰 추출
        sso_token = None
        if auth_header and auth_header.startswith("Bearer "):
            sso_token = auth_header.split(" ")[1]

        if not sso_token:
            return Identity(type=IdentityType.UNKNOWN)

        # 2. Bearer 토큰 파싱 및 정밀 검증
        # Admin/User용 토큰은 서명 검증을 시도하고, 에이전트용은 페이로드만 추출합니다.
        payload = self.jwt_service.decode_and_verify(sso_token)
        if not payload:
            payload = self.jwt_service.extract_payload(sso_token)

        if not payload:
            return Identity(type=IdentityType.UNKNOWN)

        # 3. 3단계 권한 판단 로직 (Super Admin / Admin / User)
        # 62e90394-69f5-4237-9190-012177145e10: Global Administrator
        # 9b89c20d-ad03-4503-ad20-039103212108: Application Administrator
        # 158c15cc-0570-44c1-848e-0f04dc22312b: Cloud Application Administrator
        # e8611eb8-c13f-4745-8462-24867d9a65ed: Privileged Role Administrator
        # fe930be7-5e62-47db-91af-98c3a49a38b1: User Administrator
        # f28a1fec-99ee-474b-8393-8cfb46ac3f29: Billing Administrator
        admin_role_ids = [
            "62e90394-69f5-4237-9190-012177145e10",
            "9b89c20d-ad03-4503-ad20-039103212108",
            "158c15cc-0570-44c1-848e-0f04dc22312b",
            "e8611eb8-c13f-4745-8462-24867d9a65ed",
            "fe930be7-5e62-47db-91af-98c3a49a38b1",
            "f28a1fec-99ee-474b-8393-8cfb46ac3f29",
        ]

        wids = payload.get("wids", [])
        if not isinstance(wids, list):
            wids = [wids]

        roles = payload.get("roles", [])
        if isinstance(roles, str):
            roles = [roles]

        # A. Super Admin 판별
        is_super = "62e90394-69f5-4237-9190-012177145e10" in wids or any(
            r in ["GlobalAdmin", "Company Administrator", "TenantAdmin"] for r in roles
        )

        # B. App Admin 판별
        is_app_admin = any(rid in wids for rid in admin_role_ids) or any(
            r in ["Admin", "Administrator", "GlobalAdmin"] for r in roles
        )

        # C. 기계 계정(CI/CD) 판별
        is_machine = (
            payload.get("idtyp") == "app" or payload.get("appid") or payload.get("azp")
        )

        # 등급 결정 (우선순위: Super > Admin > Machine > User)
        if is_super:
            identity_type = IdentityType.GLOBAL_ADMIN
        elif is_app_admin:
            identity_type = IdentityType.APP_ADMIN
        elif is_machine:
            identity_type = IdentityType.CI_CD
        else:
            identity_type = (
                IdentityType.CLIENT_AGENT
            )  # 일반 사용자(명칭은 에이전트와 혼용되나 실제론 유저)

        return Identity(
            type=identity_type,
            id=payload.get("oid") or payload.get("sub"),
            name=payload.get("name")
            or payload.get("preferred_username")
            or payload.get("appid"),
            email=payload.get("preferred_username") or payload.get("upn"),
            roles=roles,
            is_global_admin=is_super,  # 하위 호환성을 위해 is_super를 is_global_admin에 매핑
            tenant_id=self._get_tenant_id(payload),
            sso_token=sso_token,
        )

    def _get_tenant_id(self, payload: dict) -> str | None:
        """
        다양한 클레임 명칭에서 테넌트 ID를 추출합니다.
        tid, tenantid, http://schemas.microsoft.com/identity/claims/tenantid 등 대응
        """
        tenant_schema = "http://schemas.microsoft.com/identity/claims/tenantid"
        tid = (
            payload.get("tid")
            or payload.get("tenantid")
            or payload.get(tenant_schema)
            or payload.get("tenant_id")
        )

        # 🛡️ [NEW] "none", "undefined", "null" 등 유효하지 않은 문자열 필터링
        if isinstance(tid, str) and tid.lower() in ["none", "undefined", "null", ""]:
            tid = None

        if tid:
            tid = tid.lower()

        if not tid:
            from structlog import get_logger

            get_logger().warning(
                "Tenant ID (tid) not found or invalid in token payload",
                tid=tid,
                available_keys=list(payload.keys()),
            )
        return tid
