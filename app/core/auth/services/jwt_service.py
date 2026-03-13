import base64
import json
import time

import jwt
from jwt import PyJWKClient
from structlog import get_logger

from app.core.config import settings
from app.core.exceptions import UnauthorizedException


class JwtService:
    """JWT 토큰 및 관련 인코딩 데이터(Base64-JSON) 연산을 담당하는 서비스"""

    def __init__(self):
        # Microsoft Jwks URL (Entra ID용)
        self.jwks_url = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
        self.jwk_client = PyJWKClient(self.jwks_url)

    def decode_base64_json(self, data: str) -> dict:
        """Base64로 인코딩된 JSON 문자열을 파싱하여 dict로 반환합니다."""
        try:
            # JWT는 URL-safe Base64를 사용하므로 '-'와 '_'를 호환 치환합니다.
            data = data.replace("-", "+").replace("_", "/")
            missing_padding = len(data) % 4
            if missing_padding:
                data += "=" * (4 - missing_padding)

            decoded_bytes = base64.b64decode(data).decode("utf-8")
            return json.loads(decoded_bytes)
        except Exception:
            return {}

    def extract_payload(self, token: str) -> dict:
        """JWT의 서명 검증 없이 페이로드만 수동으로 추출하되 제한적인 만료(exp) 검증을 수행합니다."""
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload = self.decode_base64_json(parts[1])

        if payload and "exp" in payload:
            expired_time = int(payload["exp"])
            if expired_time < time.time():
                get_logger().warning(
                    "JWT has expired in extract_payload", exp=expired_time
                )
                raise UnauthorizedException(
                    "AUTH_REQUIRED|Authentication token has expired. Please login again."
                )

        return payload

    def decode_and_verify(self, token: str) -> dict | None:
        """
        토큰의 서명을 Microsoft 위임 키로 검증하고 페이로드를 반환합니다.
        Easy Auth가 꺼져있을 때 직접 토큰을 검증하기 위해 사용합니다.
        """
        try:
            signing_key = self.jwk_client.get_signing_key_from_jwt(token)

            # Teams SSO 토큰(`api://`) 또는 Azure Management 토큰(`https://management.azure.com`) 모두 허용
            audience = f"api://{settings.CLIENT_ID}"
            allowed_audiences = [audience, settings.CLIENT_ID, "https://management.azure.com/", "https://management.azure.com"]

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=allowed_audiences,
                options={"verify_exp": True, "verify_aud": True},
            )
            return payload
        except Exception as e:
            from structlog import get_logger
            logger = get_logger()

            # 실패 원인 분석을 위해 토큰 내 aud 클레임을 수동으로 확인
            raw_payload = self.extract_payload(token)
            actual_aud = raw_payload.get("aud")
            expected_auds = [f"api://{settings.CLIENT_ID}", settings.CLIENT_ID, "https://management.azure.com/"]

            logger.warning(
                "JWT verification failed",
                error=str(e),
                actual_aud=actual_aud,
                expected_auds=expected_auds,
                client_id_from_env=settings.CLIENT_ID
            )
            return None
