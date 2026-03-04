import json
import time

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(time.time()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # 요청 본문 읽기 (바디를 소모하므로 나중에 다시 사용할 수 있게 복사 필요)
        body = await self._get_request_body(request)
        
        start_time = time.time()
        
        logger.info(
            "Incoming request",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            body=body if request.method in ["POST", "PUT", "PATCH"] else None
        )

        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception("Request failed", path=request.url.path)
            raise e

        process_time = time.time() - start_time
        
        # 응답 본문은 읽기가 까다로움 (Stream인 경우 등)
        # 일단 상태 코드와 소요 시간 위주로 로깅
        logger.info(
            "Outgoing response",
            status_code=response.status_code,
            process_time=f"{process_time:.4f}s"
        )
        
        return response

    async def _get_request_body(self, request: Request):
        if request.method not in ["POST", "PUT", "PATCH"]:
            return None
        
        try:
            body = await request.body()
            # 바디를 다시 사용할 수 있게 설정 (FastAPI 내부 바디 소모 방지)
            async def receive() -> Message:
                return {"type": "http.request", "body": body}
            request._receive = receive
            
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body.decode("utf-8") if body else None
        except Exception:
            return "[Unable to read body]"