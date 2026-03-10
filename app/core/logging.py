import sys

import structlog


def setup_logging():
    """
    애플리케이션을 위한 구조화된 로깅을 설정합니다.
    운영 환경에서는 JSON 로그를 출력하고, 개발 환경에서는 읽기 쉬운 콘솔 로그를 출력합니다.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if sys.stderr.isatty():
        # 로컬 개발을 위한 가독성 좋은 출력
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
        ]
    else:
        # 운영 환경(Splunk/ELK 등)을 위한 JSON 로그
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 표준 라이브러리 로깅 가로채기
    import logging

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """지정된 이름의 로거를 반환합니다."""
    return structlog.get_logger(name)
