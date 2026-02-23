import base64
import json


class JwtService:
    """JWT 토큰 및 관련 인코딩 데이터(Base64-JSON) 연산을 담당하는 서비스"""

    def decode_base64_json(self, data: str) -> dict:
        """Base64로 인코딩된 JSON 문자열을 파싱하여 dict로 반환합니다."""
        try:
            # Base64 패딩 수정
            missing_padding = len(data) % 4
            if missing_padding:
                data += "=" * (4 - missing_padding)

            decoded_bytes = base64.b64decode(data).decode("utf-8")
            return json.loads(decoded_bytes)
        except Exception:
            return {}

    def extract_payload(self, token: str) -> dict:
        """JWT의 서명 검증 없이 페이로드만 수동으로 추출합니다."""
        parts = token.split(".")
        if len(parts) != 3:
            return {}

        return self.decode_base64_json(parts[1])
