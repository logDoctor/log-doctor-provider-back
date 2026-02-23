from .dependencies import (
    get_admin_verifier,
    get_identity_extractor,
    get_jwt_service,
    get_tenant_verifier,
    get_token_provider,
)
from .guards import (
    admin_required,
    check_admin,
    check_tenant,
    get_current_identity,
    get_sso_token,
    identity_required,
    tenant_verified,
    token_required,
)
from .models import Identity, IdentityType

__all__ = [
    "check_admin",
    "admin_required",
    "check_tenant",
    "tenant_verified",
    "get_sso_token",
    "token_required",
    "get_current_identity",
    "identity_required",
    "get_identity_extractor",
    "get_admin_verifier",
    "get_tenant_verifier",
    "get_jwt_service",
    "get_token_provider",
    "get_obo_access_token",
    "Identity",
    "IdentityType",
]


async def get_obo_access_token(sso_token: str) -> str:
    """SSO 토큰을 On-Behalf-Of 액세스 토큰으로 교환하는 편의 함수"""
    provider = get_token_provider()
    return await provider.get_obo_token(sso_token)
