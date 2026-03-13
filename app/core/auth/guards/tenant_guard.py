from fastapi import Depends, Request

from app.core import (
    BadRequestException,
    ForbiddenException,
    UnauthorizedException,
)

from ..dependencies import get_tenant_verifier
from ..models import Identity
from .identity_guard import get_current_identity


async def check_tenant(
    request: Request,
    identity: Identity = Depends(get_current_identity),
    tenant_verifier=Depends(get_tenant_verifier),
) -> str:
    """ClientAgent의 신분과 테넌트 정합성을 검증하는 의존성 주입 함수입니다. (Internal dependency)"""
    token_tid = identity.tenant_id
    if not token_tid:
        raise ForbiddenException(
            "Tenant ID is missing from authentication information."
        )

    req_tid = None
    try:
        body = await request.json()
        req_tid = body.get("tenant_id")
    except Exception:
        req_tid = request.query_params.get("tenant_id")

    if not req_tid:
        raise BadRequestException("tenant_id is missing.")

    try:
        return tenant_verifier.verify_tenant_match(token_tid, req_tid)
    except UnauthorizedException as e:
        raise ForbiddenException(str(e)) from e
