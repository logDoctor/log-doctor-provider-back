from typing import Any

from app.domains.tenant.repository import TenantRepository, UserRepository


class UserSyncService:
    """
    검증된 토큰의 클레임 정보를 기반으로 사용자와 테넌트를 DB에 동기화합니다.
    """

    def __init__(
        self, tenant_repository: TenantRepository, user_repository: UserRepository
    ) -> None:
        self.tenant_repo = tenant_repository
        self.user_repo = user_repository

    async def execute(self, oid: str, tid: str, name: str) -> dict[str, Any]:
        """
        1. Tenant 존재 여부를 확인하고 없으면 신규 생성합니다.
        2. User 존재 여부(oid 기준)를 확인하고 없으면 신규 생성합니다.
        """
        # 1. Tenant 확인 혹은 생성
        tenant = await self.tenant_repo.get_by_id(tid)
        if not tenant:
            tenant = await self.tenant_repo.create(tenant_id=tid)

        # 2. User 확인 혹은 생성
        user = await self.user_repo.get_by_oid(oid=oid, tenant_id=tid)
        if not user:
            user = await self.user_repo.create(oid=oid, tenant_id=tid, name=name)

        return user
