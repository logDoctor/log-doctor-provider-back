from structlog import get_logger

from app.core.config import settings

from ..constants import AppRoleName, AzureDirectoryRole, TokenClaim
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

        payload = self.jwt_service.decode_and_verify(sso_token)
        if not payload:
            get_logger().warning(
                "Identity extraction failed: JWT verification returned None. "
                "Check JwtService logs for 'Audience doesn't match' or other verification errors."
            )
            return Identity(type=IdentityType.UNKNOWN)

        tid = self._get_tenant_id(payload)
        is_platform_tenant = self._is_platform_tenant(tid)

        wids = payload.get(TokenClaim.WIDS, [])
        if not isinstance(wids, list):
            wids = [wids]

        groups = payload.get(TokenClaim.GROUPS, [])
        if isinstance(groups, str):
            groups = [groups]

        roles = payload.get(TokenClaim.ROLES, [])
        if isinstance(roles, str):
            roles = [roles]

        # 1. wids와 groups를 뒤져서 "Azure 전역 관리자"인지 확인 (ID로 비교)
        is_directory_admin = self._is_directory_admin(wids, groups)

        # 2. 사용자 정보(UPN, Email 등)가 전혀 없고 APPID/AZP만 있는 경우 "기계(Machine)" 신원으로 판별
        # (Entra ID에서 발급한 앱 전용 토근 특징)
        is_machine = self._is_machine(payload)

        # 3. roles를 뒤져서 "우리 앱 전담 관리자"인지 확인 (문자열로 비교)
        identity_type = self._resolve_identity_type(
            roles, is_directory_admin, is_platform_tenant, is_machine
        )

        return Identity(
            type=identity_type,
            id=payload.get(TokenClaim.OID) or payload.get(TokenClaim.SUB),
            name=payload.get(TokenClaim.NAME)
            or payload.get(TokenClaim.PREFERRED_USERNAME)
            or payload.get(TokenClaim.APPID),
            email=payload.get(TokenClaim.PREFERRED_USERNAME)
            or payload.get(TokenClaim.UPN),
            roles=roles,
            wids=wids,
            groups=groups,
            tenant_id=tid,
            sso_token=sso_token,
        )

    def _is_directory_admin(self, wids: list[str], groups: list[str]) -> bool:
        """
        wids(Directory Roles)와 groups를 뒤져서 "Azure 전역 관리자"인지 확인합니다.
        Azure AD에서 사전에 정의된 고유 ID(UUID)를 기반으로 비교합니다.
        """
        combined_indicators = set(wids) | set(groups)
        return any(
            rid in AzureDirectoryRole.ADMIN_CONSENT_CAPABLE_ROLES
            for rid in combined_indicators
        )

    def _resolve_identity_type(
        self,
        roles: list[str],
        is_directory_admin: bool,
        is_platform_tenant: bool,
        is_machine: bool,
    ) -> IdentityType:
        """
        App Role과 Azure Directory Role을 결합하여 최종 신원 유형을 결정합니다.
        """

        # 앱 전용 역할(App Roles) 확인
        is_platform_role = AppRoleName.PLATFORM_ADMIN in roles
        is_tenant_role = AppRoleName.TENANT_ADMIN in roles
        is_privileged_role = AppRoleName.PRIVILEGED_USER in roles

        # 1. 플랫폼 관리자 (Platform Provider)
        if is_platform_tenant and (
            is_platform_role or is_tenant_role or is_directory_admin
        ):
            return IdentityType.PLATFORM_ADMIN

        # 2. 테넌트 관리자 (Customer Administrator)
        if is_tenant_role or is_directory_admin:
            return IdentityType.TENANT_ADMIN

        # 3. 위임된 운영자 (Privileged User)
        if is_privileged_role:
            return IdentityType.PRIVILEGED_USER

        # 4. 자동화 기계 신원 (CI/CD / Service Principal)
        if is_machine:
            return IdentityType.CI_CD

        # 5. 일반 사용자 (Default)
        return IdentityType.USER

    def _is_platform_tenant(self, tid: str | None) -> bool:
        """
        현재 테넌트가 플랫폼 운영사의 테넌트인지 확인합니다.
        """
        return (
            tid is not None
            and settings.TENANT_ID is not None
            and tid.lower() == settings.TENANT_ID.lower()
        )

    def _is_machine(self, payload: dict) -> bool:
        return (
            not payload.get(TokenClaim.UPN)
            and not payload.get(TokenClaim.PREFERRED_USERNAME)
            and (payload.get(TokenClaim.APPID) or payload.get(TokenClaim.AZP))
        )

    def _get_tenant_id(self, payload: dict) -> str | None:
        """
        다양한 클레임 명칭에서 테넌트 ID를 추출합니다.
        """
        tid = (
            payload.get(TokenClaim.TID)
            or payload.get(TokenClaim.TENANTID)
            or payload.get(TokenClaim.MICROSOFT_TENANT_SCHEMA)
            or payload.get(TokenClaim.TENANT_ID)
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
