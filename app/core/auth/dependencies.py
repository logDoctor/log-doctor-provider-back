from functools import lru_cache

from azure.identity.aio import DefaultAzureCredential

from app.core.config import settings
from app.core.exceptions import InternalServerException

from .services.auth_provider import (
    EntraIDTokenProvider,
    MockTokenProvider,
    TokenProvider,
)
from .services.graph_service import GraphService
from .services.identity_extractor import IdentityExtractor
from .services.jwt_service import JwtService
from .services.tenant_verifier import TenantVerifier


@lru_cache
def get_jwt_service() -> JwtService:
    """JWT 연산 서비스를 생성하여 반환합니다."""
    return JwtService()


@lru_cache
def get_graph_service() -> GraphService:
    """TokenProvider가 주입된 GraphService 인스턴스를 반환합니다."""
    return GraphService(get_token_provider())


@lru_cache
def get_identity_extractor() -> IdentityExtractor:
    """신원 추출 서비스를 생성하여 반환합니다."""
    return IdentityExtractor(get_jwt_service())


@lru_cache
def get_tenant_verifier() -> TenantVerifier:
    """테넌트 정합성 검증 서비스를 생성하여 반환합니다."""
    return TenantVerifier()


@lru_cache
def get_token_provider() -> TokenProvider:
    if settings.AUTH_METHOD == "mock":
        return MockTokenProvider()

    if not settings.CLIENT_SECRET:
        raise InternalServerException(
            "CLIENT_SECRET is required for OBO token exchange. "
            "Even if AUTH_METHOD is 'managed_identity', client secret must be set "
            "for OBO flows."
        )

    return EntraIDTokenProvider(
        jwt_service=get_jwt_service(),
        client_secret=settings.CLIENT_SECRET,
    )


_azure_credential = None


async def get_azure_credential() -> DefaultAzureCredential:
    """DefaultAzureCredential 싱글톤 인스턴스를 반환합니다."""
    global _azure_credential
    if _azure_credential is None:
        _azure_credential = DefaultAzureCredential()
    return _azure_credential
