from ..models import Identity, IdentityType
from .jwt_service import JwtService


class IdentityExtractor:
    """헤더 정보를 바탕으로 호출자의 신원을 추출하는 전담 클래스"""

    def __init__(self, jwt_service: JwtService):
        self.jwt_service = jwt_service

    def extract(self, x_ms_principal: str | None, auth_header: str | None) -> Identity:
        # 1. Bearer 토큰 추출 (OBO 검증을 위해 항상 필요함)
        sso_token = None
        if auth_header and auth_header.startswith("Bearer "):
            sso_token = auth_header.split(" ")[1]

        # 2. Azure EasyAuth 헤더(인프라 레벨) 파싱
        if x_ms_principal:
            data = self.jwt_service.decode_base64_json(x_ms_principal)
            if data:
                identity = self._build_identity_from_claims(data.get("claims", []), IdentityType.ADMIN)
                identity.sso_token = sso_token # 인증 방식에 상관없이 OBO를 위한 토큰 보관
                return identity

        # 3. Bearer 토큰 파싱 (Easy Auth가 꺼져있거나 에이전트 요청인 경우)
        if sso_token:
            # 먼저 서명을 포함한 정밀 검증 시도 (Admin/User 토큰 대상)
            payload = self.jwt_service.decode_and_verify(sso_token)
            
            if payload:
                # 서명이 유효한 사용자 토큰인 경우 (ADMIN)
                wids = payload.get("wids", [])
                # 62e90394-69f5-4237-9190-012177145e10 은 Entra ID의 Global Administrator Role ID 입니디.
                is_global_admin = "62e90394-69f5-4237-9190-012177145e10" in wids

                return Identity(
                    type=IdentityType.ADMIN,
                    id=payload.get("oid") or payload.get("sub"),
                    name=payload.get("name"),
                    email=payload.get("preferred_username") or payload.get("upn"),
                    roles=payload.get("roles", []),
                    is_global_admin=is_global_admin,
                    tenant_id=self._get_tenant_id(payload),
                    sso_token=sso_token,
                )
            
            # 서명 검증에 실패했거나 에이전트용 토큰인 경우 (기존 로직 유지)
            payload = self.jwt_service.extract_payload(sso_token)
            if payload:
                # roles 추출 (CI-CD 파이프라인 등에서 부여된 권한)
                roles = payload.get("roles", [])
                if isinstance(roles, str):
                    roles = [roles]
 
                # CI-CD 파이프라인(App Registration) 식별
                is_machine = (
                    payload.get("idtyp") == "app"
                    or payload.get("appid")
                    or payload.get("azp")
                )
                identity_type = (
                    IdentityType.CI_CD if is_machine else IdentityType.CLIENT_AGENT
                )
 
                # [FIX] 폴백 블록에서도 전역 관리자 권한 체크 수행
                wids = payload.get("wids", [])
                is_global_admin = "62e90394-69f5-4237-9190-012177145e10" in wids

                return Identity(
                    type=identity_type,
                    id=payload.get("oid") or payload.get("sub"),
                    name=payload.get("appid") or payload.get("azp"),  # 호출한 앱 ID
                    email=payload.get("preferred_username") or payload.get("upn"),
                    roles=roles,
                    is_global_admin=is_global_admin,
                    tenant_id=self._get_tenant_id(payload),
                    sso_token=sso_token,
                )
 
        return Identity(type=IdentityType.UNKNOWN)

    def _build_identity_from_claims(self, claims_list: list[dict], identity_type: IdentityType) -> Identity:
        """Azure EasyAuth 스타일의 클레임 리스트에서 Identity를 생성합니다."""
        claims = {c["typ"]: c["val"] for c in claims_list}
        role_schema = "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
        roles = [c["val"] for c in claims_list if c["typ"] in ("roles", role_schema)]

        return Identity(
            type=identity_type,
            id=claims.get("http://schemas.microsoft.com/identity/claims/objectidentifier") or claims.get("oid"),
            name=claims.get("name"),
            email=claims.get("preferred_username") or claims.get("upn") or claims.get("http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name"),
            roles=roles,
            tenant_id=self._get_tenant_id(claims),
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
                available_keys=list(payload.keys())
            )
        return tid
