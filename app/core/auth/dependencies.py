from .services.admin_verifier import AdminVerifier
from .services.auth_provider import EntraIDTokenProvider, TokenProvider
from .services.identity_extractor import IdentityExtractor
from .services.jwt_service import JwtService
from .services.tenant_verifier import TenantVerifier

# --- 서비스 공급자 (Factories / Low-level Dependencies) ---


def get_jwt_service() -> JwtService:
    """JWT 연산 서비스를 생성하여 반환합니다."""
    return JwtService()


def get_identity_extractor() -> IdentityExtractor:
    """신원 추출 서비스를 생성하여 반환합니다."""
    return IdentityExtractor(jwt_service=get_jwt_service())


def get_admin_verifier() -> AdminVerifier:
    """관리자 권한 검증 서비스를 생성하여 반환합니다."""
    return AdminVerifier()


def get_tenant_verifier() -> TenantVerifier:
    """테넌트 정합성 검증 서비스를 생성하여 반환합니다."""
    return TenantVerifier()


def get_token_provider() -> TokenProvider:
    """토큰 발급 제공자(Entra ID 등)를 생성하여 반환합니다."""
    return EntraIDTokenProvider()
