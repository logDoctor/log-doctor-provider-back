from ..models import Identity, IdentityType
from .jwt_service import JwtService


class IdentityExtractor:
    """헤더 정보를 바탕으로 호출자의 신원을 추출하는 전담 클래스"""

    def __init__(self, jwt_service: JwtService):
        self.jwt_service = jwt_service

    def extract(self, x_ms_principal: str | None, auth_header: str | None) -> Identity:
        # 1. Azure EasyAuth 헤더(운영자) 파싱
        if x_ms_principal:
            data = self.jwt_service.decode_base64_json(x_ms_principal)
            if data:
                claims = {c["typ"]: c["val"] for c in data.get("claims", [])}

                # 역할(Role) 추출
                role_schema = (
                    "http://schemas.microsoft.com/ws/2008/06/identity/claims/role"
                )
                roles = [
                    c["val"]
                    for c in data.get("claims", [])
                    if c["typ"] in ("roles", role_schema)
                ]

                return Identity(
                    type=IdentityType.ADMIN,
                    id=claims.get(
                        "http://schemas.microsoft.com/identity/claims/objectidentifier"
                    )
                    or claims.get("oid"),
                    name=claims.get("name") or claims.get("preferred_username"),
                    roles=roles,
                    tenant_id=claims.get(
                        "http://schemas.microsoft.com/identity/claims/tenantid"
                    )
                    or claims.get("tid"),
                )

        # 2. Bearer 토큰 파싱 (머신/에이전트/CI-CD)
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            payload = self.jwt_service.extract_payload(token)

            if payload:
                # roles 추출 (CI-CD 파이프라인 등에서 부여된 권한)
                roles = payload.get("roles", [])
                if isinstance(roles, str):
                    roles = [roles]

                # CI-CD 파이프라인(App Registration) 식별
                # idtyp == "app" 이거나 특정 CI/CD용 Client ID인 경우 CI_CD 타입으로 분류
                is_machine = (
                    payload.get("idtyp") == "app"
                    or payload.get("appid")
                    or payload.get("azp")
                )
                identity_type = (
                    IdentityType.CI_CD if is_machine else IdentityType.CLIENT_AGENT
                )

                return Identity(
                    type=identity_type,
                    id=payload.get("oid") or payload.get("sub"),
                    name=payload.get("appid") or payload.get("azp"),  # 호출한 앱 ID
                    roles=roles,
                    tenant_id=payload.get("tid"),
                )

        return Identity(type=IdentityType.UNKNOWN)
