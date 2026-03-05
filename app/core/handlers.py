import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import LogDoctorException
from app.core.i18n import get_locale, translate

logger = structlog.get_logger()


async def log_doctor_exception_handler(request: Request, exc: LogDoctorException):
    """
    LogDoctorException을 처리하고 구조화된 JSON 응답을 반환합니다.
    """
    locale = get_locale(request)
    translated_message = translate(exc.message, locale)
    
    logger.warning("LogDoctorException occurred", code=exc.code, message=translated_message, path=request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": translated_message,
                "path": request.url.path,
            }
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Pydantic 검증 오류(422) 발생 시 상세 내용을 로깅합니다.
    """
    errors = exc.errors()
    
    logger.error("Validation Error (422)", path=request.url.path, errors=errors)
    
    locale = get_locale(request)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": translate("VALIDATION_ERROR", locale),
                "details": errors,
                "path": request.url.path,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    처리되지 않은 예외를 처리하고 500 내부 서버 오류를 반환합니다.
    """
    print(f"처리되지 않은 예외: {exc}")
    locale = get_locale(request)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": translate("INTERNAL_SERVER_ERROR", locale),
                "path": request.url.path,
            }
        },
    )
