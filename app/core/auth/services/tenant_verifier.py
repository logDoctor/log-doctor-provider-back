from .admin_verifier import AuthError


class TenantVerifier:
    """테넌트 정합성을 검증하는 순수 서비스 클래스 (프레임워크 독립적)"""

    def verify_tenant_match(self, token_tid: str, req_tid: str) -> str:
        """
        토큰의 테넌트 ID와 요청의 테넌트 ID가 일치하는지 확인합니다.
        일치하지 않을 경우 AuthError를 발생시킵니다.
        """
        if not token_tid or not req_tid:
            raise AuthError("테넌트 ID 검증을 위한 정보가 누락되었습니다.")

        if token_tid != req_tid:
            raise AuthError(
                f"테넌트 ID가 일치하지 않습니다. (Token: {token_tid} vs Request: {req_tid})"
            )

        return token_tid
