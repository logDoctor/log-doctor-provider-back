import msal

from app.core.config import settings
from .services.admin_verifier import AdminVerifier
from .services.auth_provider import EntraIDTokenProvider, MockTokenProvider, TokenProvider
from .services.identity_extractor import IdentityExtractor
from .services.jwt_service import JwtService
from .services.tenant_verifier import TenantVerifier
from .services.graph_service import GraphService

# --- 서비스 공급자 (Factories / Low-level Dependencies) ---


def get_jwt_service() -> JwtService:
    """JWT 연산 서비스를 생성하여 반환합니다."""
    return JwtService()

def get_graph_service() -> GraphService:
    """무상태 GraphService 인스턴스를 반환합니다."""
    return GraphService()

def get_identity_extractor() -> IdentityExtractor:
    """신원 추출 서비스를 생성하여 반환합니다."""
    return IdentityExtractor(get_jwt_service())


def get_admin_verifier() -> AdminVerifier:
    """관리자 권한 검증 서비스를 생성하여 반환합니다."""
    return AdminVerifier()


def get_tenant_verifier() -> TenantVerifier:
    """테넌트 정합성 검증 서비스를 생성하여 반환합니다."""
    return TenantVerifier()


def get_token_provider() -> TokenProvider:
    if settings.AUTH_METHOD == "mock":
        return MockTokenProvider()

    client_credential = None
    if settings.AUTH_METHOD == "secret":
        client_credential = settings.CLIENT_SECRET
    elif settings.AUTH_METHOD == "managed_identity":
        client_credential = msal.SystemAssignedManagedIdentity()

    return EntraIDTokenProvider(
        jwt_service=get_jwt_service(),
        client_credential=client_credential
    )
