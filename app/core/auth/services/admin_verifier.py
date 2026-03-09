from ..models import Identity, IdentityType


class AuthError(Exception):
    """인증/인가 관련 비즈니스 예외"""

    pass


class AdminVerifier:
    """관리자 권한 여부를 검증하는 순수 서비스 클래스 (프레임워크 독립적)"""

    def verify(self, identity: Identity) -> Identity:
        """
        제공된 신원이 관리자인지 확인합니다.
        관리자가 아닐 경우 AuthError를 발생시킵니다.
        """
        if identity.type not in (
            IdentityType.GLOBAL_ADMIN,
            IdentityType.APP_ADMIN,
            IdentityType.CI_CD,
        ):
            raise AuthError("관리자 권한이 필요합니다.")
        return identity
