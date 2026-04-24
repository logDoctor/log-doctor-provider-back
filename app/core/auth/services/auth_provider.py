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
    async def get_obo_token(
        self, sso_token: str, scopes: list[str] | None = None
    ) -> str:
        """SSO 토큰을 On-Behalf-Of 액세스 토큰으로 교환합니다."""
        pass

    @abstractmethod
    async def get_app_token(
        self, tid: str = "common", scopes: list[str] | None = None
    ) -> str:
        """클라이언트 자격 증명을 사용하여 앱 전역 권한 토큰을 획득합니다."""
        pass

    @abstractmethod
    async def get_bot_token(self) -> str:
        """Teams Bot Framework용 전용 토큰을 획득합니다."""
        pass


class MockTokenProvider(TokenProvider):
    """로컬 개발 및 테스트를 위한 가짜 토큰 발급 구현체"""

    async def get_obo_token(
        self, sso_token: str, scopes: list[str] | None = None
    ) -> str:
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

    async def get_bot_token(self) -> str:
        logger.info("Mock authentication method detected, returning dummy bot token")
        return "mock_bot_token"


class EntraIDTokenProvider(TokenProvider):
    """Azure Entra ID를 사용한 토큰 발급 구현체"""

    def __init__(self, jwt_service: JwtService, client_secret: str):
        self.jwt_service = jwt_service
        self._client_secret = client_secret

    async def get_obo_token(
        self, sso_token: str, scopes: list[str] | None = None
    ) -> str:
        payload = self.jwt_service.extract_payload(sso_token)

        final_scopes = scopes or ["https://management.azure.com/user_impersonation"]
        target_resource = "ARM" if "management.azure.com" in final_scopes[0] else "GRAPH"

        if self._is_token_already_for_target(payload, target_resource):
            logger.info(f"Target {target_resource} token already present, skipping OBO exchange")
            return sso_token

        tid = payload.get("tid") or "common"
        authority = f"https://login.microsoftonline.com/{tid}"

        app = msal.ConfidentialClientApplication(
            settings.CLIENT_ID,
            authority=authority,
            client_credential=self._client_secret,
        )

        try:
            result = app.acquire_token_on_behalf_of(
                user_assertion=sso_token, scopes=final_scopes
            )
        except Exception as e:
            logger.error("MSAL OBO system error", error=str(e))
            raise UnauthorizedException(
                "An error occurred while connecting to the authentication service."
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
            f"Failed to acquire app-only token: {result.get('error')}"
        )

    async def get_bot_token(self) -> str:
        """Teams Bot Framework용 전용 토큰을 획득합니다."""
        # Azure Bot 리소스가 Single-Tenant 유형이므로 홈 테넌트 Authority 인증이 필요합니다.
        tid = getattr(settings, "TENANT_ID", "common")
        authority = f"https://login.microsoftonline.com/{tid}"
        scopes = ["https://api.botframework.com/.default"]

        app = msal.ConfidentialClientApplication(
            settings.CLIENT_ID,
            authority=authority,
            client_credential=self._client_secret,
        )

        # 봇 토큰은 클라이언트 자격 증명(Client Credentials) 흐름을 사용합니다.
        result = app.acquire_token_for_client(scopes=scopes)

        if "access_token" in result:
            return result.get("access_token")

        logger.error(
            "Failed to acquire bot token",
            error=result.get("error"),
            desc=result.get("error_description"),
        )
        raise UnauthorizedException(
            f"Failed to acquire bot token: {result.get('error')}"
        )

    def _is_token_already_for_target(self, payload: dict, target: str) -> bool:
        """
        토큰이 이미 목표 리소스(Graph 혹은 ARM)용인지 확인합니다.
        
        오디언스(aud)가 백엔드 자신의 Client ID라면 이는 'Identity/Middle-tier' 토큰이므로 
        반드시 OBO 교환을 거쳐야 합니다.
        """
        audience = payload.get("aud", "")
        # v1.0 토큰은 scp, v2.0 토큰은 roles 혹은 scp에 권한이 들어있을 수 있음
        scp = payload.get("scp", "")

        # 1. ARM 타겟 확인
        if target == "ARM":
            is_arm_aud = audience in [
                "https://management.azure.com/",
                "https://management.azure.com",
                "https://management.core.windows.net/",
            ]
            return is_arm_aud or "user_impersonation" in scp

        # 2. Graph 타겟 확인
        if target == "GRAPH":
            is_graph_aud = audience in [
                "https://graph.microsoft.com",
                "https://graph.microsoft.com/",
                "00000003-0000-0000-c000-000000000000",
            ]
            return is_graph_aud

        return False

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
