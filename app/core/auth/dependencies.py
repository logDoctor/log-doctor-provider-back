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

    # OBO 흐름은 AUTH_METHOD와 관계없이 항상 client_secret이 필요합니다.
    # Managed Identity는 Azure 리소스(Cosmos DB, Blob 등) 접근용이며,
    # MSAL OBO 교환에는 사용할 수 없습니다.
    if not settings.CLIENT_SECRET:
        raise RuntimeError(
            "OBO 토큰 교환을 위해 CLIENT_SECRET 환경 변수가 필요합니다. "
            "AUTH_METHOD가 'managed_identity'이더라도 OBO 흐름에서는 "
            "client secret이 반드시 설정되어야 합니다."
        )

    return EntraIDTokenProvider(
        jwt_service=get_jwt_service(),
        client_secret=settings.CLIENT_SECRET,
    )
