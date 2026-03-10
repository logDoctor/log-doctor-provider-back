from app.core.config import settings

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
        sso_token = None
        if auth_header and auth_header.startswith("Bearer "):
            sso_token = auth_header.split(" ")[1]

        if not sso_token:
            return Identity(type=IdentityType.UNKNOWN)

        # Admin/User용 토큰은 서명 검증을 시도하고, 에이전트용은 페이로드만 추출합니다.
        is_verified = True
        payload = self.jwt_service.decode_and_verify(sso_token)
        if not payload:
            is_verified = False
            payload = self.jwt_service.extract_payload(sso_token)

        if not payload:
            return Identity(type=IdentityType.UNKNOWN)

        tid = self._get_tenant_id(payload)
        is_platform_tenant = (
            tid is not None
            and settings.TENANT_ID is not None
            and tid.lower() == settings.TENANT_ID.lower()
        )
        # TODO: 운영팀이 별도 테넌트(B)를 사용할 경우, settings.TENANT_ID와의 비교 로직을 허용 테넌트 리스트 체크로 확장해야 함.

        admin_role_ids = [
            "62e90394-69f5-4237-9190-012177145e10",  # Global Administrator
            "9b89c20d-ad03-4503-ad20-039103212108",  # Application Administrator
            "158c15cc-0570-44c1-848e-0f04dc22312b",  # Cloud Application Administrator
            "e8611eb8-c13f-4745-8462-24867d9a65ed",  # Privileged Role Administrator
            "fe930be7-5e62-47db-91af-98c3a49a38b1",  # User Administrator
            "f28a1fec-99ee-474b-8393-8cfb46ac3f29",  # Billing Administrator
        ]

        wids = payload.get("wids", [])
        if not isinstance(wids, list):
            wids = [wids]

        roles = payload.get("roles", [])
        if isinstance(roles, str):
            roles = [roles]

        # 관리자 역할 보유 여부 확인
        has_admin_role = any(rid in wids for rid in admin_role_ids) or any(
            r
            in [
                "GlobalAdmin",
                "Company Administrator",
                "TenantAdmin",
                "Admin",
                "Administrator",
            ]
            for r in roles
        )

        # 기계 계정(CI/CD) 판별
        # 🛡️ [SECURITY] azp/appid는 일반 사용자 토큰에도 항상 포함되므로, 이것만으로 기계 계정이라 판단하면 위험합니다.
        # v2 토큰의 idtyp 클레임을 우선하거나, 사용자 정보(upn, preferred_username)가 없는 경우로 한정합니다.
        is_machine = payload.get("idtyp") == "app" or (
            not payload.get("upn")
            and not payload.get("preferred_username")
            and (payload.get("appid") or payload.get("azp"))
        )

        # 등급 결정 (우선순위: Platform > Tenant > Machine > User)
        if has_admin_role and is_platform_tenant:
            identity_type = IdentityType.PLATFORM_ADMIN
        elif has_admin_role:
            identity_type = IdentityType.TENANT_ADMIN
        elif is_machine:
            identity_type = IdentityType.CI_CD
        else:
            identity_type = IdentityType.USER

        # 🛡️ [SECURITY] 서명 검증에 실패한 토큰인 경우, 권한을 부여하지 않고 UNKNOWN으로 처리합니다.
        if not is_verified:
            identity_type = IdentityType.UNKNOWN

        return Identity(
            type=identity_type,
            id=payload.get("oid") or payload.get("sub"),
            name=payload.get("name")
            or payload.get("preferred_username")
            or payload.get("appid"),
            email=payload.get("preferred_username") or payload.get("upn"),
            roles=roles,
            tenant_id=tid,
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
