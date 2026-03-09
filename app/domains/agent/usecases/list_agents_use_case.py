from app.core.auth import Identity, IdentityType

from ..models import Agent
from ..repository import AgentRepository


class ListAgentsUseCase:
    def __init__(self, repository: AgentRepository):
        self.repository = repository

    async def execute(
        self,
        identity: Identity,
        tenant_id: str | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> tuple[list[Agent], int]:
        """시나리오별 보안 검증을 수행하고 에이전트 목록을 조회합니다."""

        # 1. 보안 검증 및 테넌트 확정
        is_admin = identity.type in (IdentityType.GLOBAL_ADMIN, IdentityType.APP_ADMIN)

        if is_admin:
            # 관리자는 모든 테넌트 조회 가능 (tenant_id가 None이면 전체)
            target_tid = tenant_id
        else:
            # 일반 사용자는 본인 테넌트만 가능
            if tenant_id and tenant_id != identity.tenant_id:
                from fastapi import HTTPException, status

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="타사 테넌트 정보를 조회할 권한이 없습니다.",
                )
            target_tid = identity.tenant_id

        # 2. 리포지토리 호출
        return await self.repository.list_agents(target_tid, skip=skip, limit=limit)
