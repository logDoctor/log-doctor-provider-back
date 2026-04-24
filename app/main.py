import sys
import traceback
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.health import router as health_router
from app.api.v1.router import v1_router
from app.core.auth.dependencies import get_azure_credential
from app.core.config import settings
from app.core.exceptions import LogDoctorException
from app.core.handlers import (
    log_doctor_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.core.middleware import LoggingMiddleware
from app.core.routing import ExcludeNoneRoute
from app.infra.db.cosmos import CosmosDB


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # 시작 시: DB 연결 및 Azure Credential 사전 로드 (Pre-warming)
    # ACA Cold Start 시 첫 번째 요청의 지연 시간을 줄이기 위함입니다.
    logger = structlog.get_logger()
    try:
        # DB 커넥션 풀 및 클라이언트 초기화
        await CosmosDB.validate_connection()
        # Azure Managed Identity/Credential 초기화 (Discovery 과정 수행)
        await get_azure_credential()
        
        logger.info("Startup pre-warming completed successfully")
    except Exception as e:
        print(f"!!! STARTUP ERROR: {e} !!!", file=sys.stderr)
        traceback.print_exc()

        logger.critical("Startup failed. Could not initialize infrastructure.")
        sys.exit(1)

    yield

    await CosmosDB.close()


app = FastAPI(
    title="Log Doctor Backend",
    version="1.0.0",
    lifespan=lifespan,
    route_class=ExcludeNoneRoute,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(LoggingMiddleware)

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_exception_handler(LogDoctorException, log_doctor_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health_router)
app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Log Doctor API is running"}
