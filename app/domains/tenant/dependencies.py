from fastapi import Depends

from app.core.security import azure_scheme

from .repository import (
    AzureTenantRepository,
    TenantRepository,
    AzureUserRepository,
    UserRepository,
)
from .usecases.get_tenant_status_use_case import GetTenantStatusUseCase
from .usecases.user_sync_service import UserSyncService


def get_tenant_repository() -> TenantRepository:
    """Returns the concrete implementation of TenantRepository."""
    return AzureTenantRepository()


def get_user_repository() -> UserRepository:
    """Returns the concrete implementation of UserRepository."""
    return AzureUserRepository()


def get_tenant_status_use_case(
    repository: TenantRepository = Depends(get_tenant_repository),
) -> GetTenantStatusUseCase:
    """Returns a GetTenantStatusUseCase instance with the injected repository."""
    return GetTenantStatusUseCase(repository)


def get_user_sync_service(
    tenant_repo: TenantRepository = Depends(get_tenant_repository),
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserSyncService:
    return UserSyncService(tenant_repository=tenant_repo, user_repository=user_repo)


async def get_current_user_and_sync(
    user=Depends(azure_scheme),
    sync_service: UserSyncService = Depends(get_user_sync_service),
) -> dict:
    """
    1. azure_scheme을 통해 프론트엔드의 JWT 토큰 서명과 만료 기간을 검증합니다.
    2. 검증된 토큰 페이로드(claims)에서 oid와 tid를 꺼내 DB(Cosmos)에 동기화합니다.
    """
    # fastapi_azure_auth User 객체에서 클레임을 안전하게 가져옵니다.
    claims = user.claims if hasattr(user, "claims") else user.dict()

    oid = claims.get("oid")
    tid = claims.get("tid")
    name = claims.get("name", claims.get("preferred_username", "Unknown"))

    if not oid or not tid:
        raise ValueError("Invalid SSO token: Missing 'oid' or 'tid'")

    # DB에 연동/생성 (Use Case 호출)
    db_user = await sync_service.execute(oid=oid, tid=tid, name=name)
    return db_user
