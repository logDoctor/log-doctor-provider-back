from fastapi import Depends, HTTPException, Request, status

from ..dependencies import get_tenant_verifier
from ..models import Identity
from ..services.admin_verifier import AuthError
from .identity_guard import get_current_identity


async def check_tenant(
    request: Request,
    identity: Identity = Depends(get_current_identity),
    verifier=Depends(get_tenant_verifier),
) -> str:
    """ClientAgent의 신분과 테넌트 정합성을 검증하는 의존성 주입 함수입니다. (Internal dependency)"""
    # 1. 신원 정보에서 테넌트 ID 확인
    token_tid = identity.tenant_id
    if not token_tid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="인증 정보(토큰/헤더)에 테넌트 ID가 누락되었습니다.",
        )

    # 2. 요청(Body/Query)에서 tenant_id 추출
    req_tid = None
    try:
        body = await request.json()
        req_tid = body.get("tenant_id")
    except Exception:
        req_tid = request.query_params.get("tenant_id")

    if not req_tid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tenant_id가 누락되었습니다.",
        )

    # 3. 비즈니스 로직(검증) 수행 - Verifier 위임
    try:
        return verifier.verify_tenant_match(token_tid, req_tid)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e



