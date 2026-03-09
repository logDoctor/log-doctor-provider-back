import structlog
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import LogDoctorException

logger = structlog.get_logger()


async def log_doctor_exception_handler(request: Request, exc: LogDoctorException):
    """
    LogDoctorException을 처리하고 구조화된 JSON 응답을 반환합니다.
    """
    logger.warning(
        "LogDoctorException occurred",
        code=exc.code,
        message=exc.message,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
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

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "요청 데이터 검증에 실패했습니다.",
                "details": errors,
                "path": request.url.path,
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """
    처리되지 않은 예외를 처리하고 500 내부 서버 오류를 반환합니다.
    """
    # 실제 환경에서는 여기서 예외 스택 트레이스를 로깅합니다.
    print(f"처리되지 않은 예외: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "예측하지 못한 오류가 발생했습니다.",
                "path": request.url.path,
            }
        },
    )
