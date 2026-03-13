from app.core.exceptions import UnauthorizedException


class TenantVerifier:
    """테넌트 정합성을 검증하는 순수 서비스 클래스 (프레임워크 독립적)"""

    def verify_tenant_match(self, token_tid: str, req_tid: str) -> str:
        """
        토큰의 테넌트 ID와 요청의 테넌트 ID가 일치하는지 확인합니다.
        일치하지 않을 경우 UnauthorizedException을 발생시킵니다.
        """
        if not token_tid or not req_tid:
            raise UnauthorizedException("Information for tenant ID verification is missing.")

        if token_tid != req_tid:
            raise UnauthorizedException(
                f"Tenant ID mismatch. (Token: {token_tid} vs Request: {req_tid})"
            )

        return token_tid
