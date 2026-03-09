from abc import ABC, abstractmethod

import msal
import structlog

from app.core.auth.services.jwt_service import JwtService
from app.core.config import settings
from app.core.exceptions import UnauthorizedException

logger = structlog.get_logger()


class TokenProvider(ABC):
    """토큰 발급자 추상 머신"""

    @abstractmethod
    async def get_obo_token(self, sso_token: str) -> str:
        """SSO 토큰을 On-Behalf-Of 액세스 토큰으로 교환합니다."""
        pass

    @abstractmethod
    async def get_app_token(
        self, tid: str = "common", scopes: list[str] | None = None
    ) -> str:
        """클라이언트 자격 증명을 사용하여 앱 전역 권한 토큰을 획득합니다."""
        pass


class MockTokenProvider(TokenProvider):
    """로컬 개발 및 테스트를 위한 가짜 토큰 발급 구현체"""

    async def get_obo_token(self, sso_token: str) -> str:
        logger.info("Mock authentication method detected, returning dummy token")
        return f"mock_token_for_{sso_token[:10]}"

    async def get_app_token(
        self, tid: str = "common", scopes: list[str] | None = None
    ) -> str:
        logger.info(
            "Mock authentication method detected, returning dummy app token",
            scopes=scopes,
        )
        return f"mock_app_token_for_{tid}"


class EntraIDTokenProvider(TokenProvider):
    """Azure Entra ID를 사용한 토큰 발급 구현체"""

    def __init__(self, jwt_service: JwtService, client_secret: str):
        self.jwt_service = jwt_service
        self._client_secret = client_secret

    async def get_obo_token(self, sso_token: str) -> str:
        payload = self.jwt_service.extract_payload(sso_token)

        if self._is_already_management_token(payload):
            logger.info("Direct Management API token detected, skipping OBO exchange")
            return sso_token

        tid = payload.get("tid") or "common"
        authority = f"https://login.microsoftonline.com/{tid}"
        scopes = ["https://management.azure.com/user_impersonation"]

        app = msal.ConfidentialClientApplication(
            settings.CLIENT_ID,
            authority=authority,
            client_credential=self._client_secret,
        )

        try:
            result = app.acquire_token_on_behalf_of(
                user_assertion=sso_token, scopes=scopes
            )
        except Exception as e:
            logger.error("MSAL OBO system error", error=str(e))
            raise UnauthorizedException(
                "인증 서비스 연결 중 오류가 발생했습니다."
            ) from None

        if "access_token" in result:
            return result.get("access_token")

        self._handle_msal_error(result)

    async def get_app_token(
        self, tid: str = "common", scopes: list[str] | None = None
    ) -> str:
        authority = f"https://login.microsoftonline.com/{tid}"
        # 기본값은 Azure Management API (기존 로직 유지용)
        final_scopes = scopes or ["https://management.azure.com/.default"]

        app = msal.ConfidentialClientApplication(
            settings.CLIENT_ID,
            authority=authority,
            client_credential=self._client_secret,
        )

        result = app.acquire_token_for_client(scopes=final_scopes)

        if "access_token" in result:
            return result.get("access_token")

        logger.error(
            "Failed to acquire app token",
            error=result.get("error"),
            desc=result.get("error_description"),
            scopes=final_scopes,
        )
        raise UnauthorizedException(
            f"앱 전용 토큰 획득에 실패했습니다: {result.get('error')}"
        )

    def _is_already_management_token(self, payload: dict) -> bool:
        """
        토큰이 이미 Azure Management API용 권한을 직접적으로 가지고 있는지 확인합니다.

        검증 기준:
        1. Audience (aud - 수신처): 토큰의 목적지가 Azure Resource Manager(ARM) API 주소인지 확인합니다.
           - https://management.azure.com/ : 일반적인 Azure 리소스 관리 주소
           - https://management.core.windows.net/ : 레거시/핵심 관리 주소
        2. Scope (scp - 권한 범위): 'user_impersonation' 권한이 이미 포함되어 있는지 확인합니다.
           - 이 권한이 있다면 사용자를 대신해 리소스를 조작할 수 있는 상태입니다.

        이 체크가 필요한 이유:
        - 프론트엔드에서 이미 ARM용 토큰을 직접 획득해서 보낸 경우, 이를 다시 OBO(On-Behalf-Of)
          교환하려고 시도하면 Azure AD(Entra ID)에서 중복/형식 오류를 발생시킵니다.
        - 개발자 도구(CLI)나 테스트 환경에서 발급받은 '마스터키'급 토큰을 바로 사용할 수 있게 해줍니다.
        """
        audience = payload.get("aud")
        scp = payload.get("scp", "")

        is_mgmt_aud = audience in [
            "https://management.azure.com/",
            "https://management.core.windows.net/",
        ]
        has_user_impersonation = "user_impersonation" in scp

        return is_mgmt_aud or has_user_impersonation

    def _handle_msal_error(self, result: dict):
        """MSAL 결과 딕셔너리에서 에러 상황을 분석하여 적절한 예외를 발생시킵니다."""
        error_code = result.get("error")
        sub_error = result.get("suberror")
        claims = result.get("claims")
        error_desc = result.get("error_description", "Authentication failed")

        # 1. MFA(다요소 인증) 요구 케이스
        is_mfa_required = (
            error_code == "interaction_required"
            or sub_error in ["mfa_required", "basic_action"]
            or "AADSTS50076" in error_desc
            or bool(claims)
        )
        if is_mfa_required:
            raise UnauthorizedException(f"MFA_REQUIRED|{claims or ''}|{error_desc}")

        # 2. 관리자/조직 동의 요구 케이스
        if "AADSTS65001" in error_desc or error_code == "consent_required":
            raise UnauthorizedException(f"CONSENT_REQUIRED|{error_desc}")

        # 3. 앱 할당 누락 케이스
        if "AADSTS50105" in error_desc:
            raise UnauthorizedException(f"ACCESS_DENIED|NOT_ASSIGNED|{error_desc}")

        # 4. 기타 에러
        raise UnauthorizedException(f"OBO Token Exchange Failed: {error_desc}")
