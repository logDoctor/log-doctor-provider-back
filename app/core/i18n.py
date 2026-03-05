from typing import Optional
from fastapi import Request

# 초기 번역 데이터 (향후 필요시 별도 JSON 파일로 분리 가능)
MESSAGES = {
    "ko": {
        "VALIDATION_ERROR": "요청 데이터 검증에 실패했습니다.",
        "INTERNAL_SERVER_ERROR": "예측하지 못한 오류가 발생했습니다.",
        "NOT_FOUND": "리소스를 찾을 수 없습니다.",
        "BAD_REQUEST": "잘못된 요청입니다.",
        "UNAUTHORIZED": "인증 정보가 없거나 유효하지 않습니다.",
        "FORBIDDEN": "접근 권한이 없습니다.",
        "CONFLICT": "리소스 충돌이 발생했습니다."
    },
    "en": {
        "VALIDATION_ERROR": "Request data validation failed.",
        "INTERNAL_SERVER_ERROR": "An unexpected error occurred.",
        "NOT_FOUND": "Resource not found.",
        "BAD_REQUEST": "Bad request.",
        "UNAUTHORIZED": "Unauthorized or invalid credentials.",
        "FORBIDDEN": "Permission denied.",
        "CONFLICT": "Resource conflict occurred."
    }
}

def get_locale(request: Request) -> str:
    """
    Accept-Language 헤더에서 가장 적절한 로케일을 추출합니다.
    기본값은 'ko'입니다.
    """
    accept_lang = request.headers.get("accept-language", "")
    if not accept_lang:
        return "ko"
    
    # 예: "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7" -> ["ko-KR", "ko", "en-US", "en"]
    languages = [l.split(";")[0].split("-")[0].lower() for l in accept_lang.split(",")]
    
    for lang in languages:
        if lang in MESSAGES:
            return lang
            
    return "ko"

def translate(key: str, locale: str = "ko") -> str:
    """
    지정된 로케일에 맞는 번역 메시지를 반환합니다.
    키가 없으면 키 자체를 반환합니다.
    """
    return MESSAGES.get(locale, MESSAGES["ko"]).get(key, MESSAGES["ko"].get(key, key))
