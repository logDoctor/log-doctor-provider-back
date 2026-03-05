class LogDoctorException(Exception):
    """Log Doctor 애플리케이션의 기본 예외 클래스입니다."""

    def __init__(
        self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundException(LogDoctorException):
    """리소스를 찾을 수 없을 때 발생하는 예외입니다."""

    def __init__(self, message: str = "NOT_FOUND"):
        super().__init__(message, code="NOT_FOUND", status_code=404)


class BadRequestException(LogDoctorException):
    """잘못된 요청일 때 발생하는 예외입니다."""

    def __init__(self, message: str = "BAD_REQUEST"):
        super().__init__(message, code="BAD_REQUEST", status_code=400)


class UnauthorizedException(LogDoctorException):
    """인증되지 않은 사용자가 접근할 때 발생하는 예외입니다."""

    def __init__(self, message: str = "UNAUTHORIZED"):
        super().__init__(message, code="UNAUTHORIZED", status_code=401)


class ForbiddenException(LogDoctorException):
    """권한이 없는 자원에 접근할 때 발생하는 예외입니다."""

    def __init__(self, message: str = "FORBIDDEN"):
        super().__init__(message, code="FORBIDDEN", status_code=403)


class ConflictException(LogDoctorException):
    """리소스가 이미 존재하거나 상태 충돌이 발생했을 때 던지는 예외입니다."""

    def __init__(self, message: str = "CONFLICT"):
        super().__init__(message, code="CONFLICT", status_code=409)
