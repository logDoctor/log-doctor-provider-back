from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.health import router as health_router
from app.api.v1.router import v1_router
from app.core.config import settings
from app.core.exceptions import LogDoctorException
from app.core.handlers import log_doctor_exception_handler, unhandled_exception_handler
from app.core.logging import setup_logging
from app.infra.db.cosmos import CosmosDB

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. 앱 시작 시 (Startup)
    setup_logging()

    try:
        await CosmosDB.validate_connection()
    except Exception as e:
        # 로컬 Mock 테스트를 위해 강제 종료를 막고 경고만 띄우기
        logger.warning(f"⚠️ Cosmos DB 연결 패스 (로컬 Mock 모드): {e}")

    yield

    # 2. 앱 종료 시 (Shutdown)
    try:
        await CosmosDB.close()
    except Exception:
        pass


app = FastAPI(title="Log Doctor Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_exception_handler(LogDoctorException, log_doctor_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(health_router)
app.include_router(v1_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Log Doctor API is running"}
