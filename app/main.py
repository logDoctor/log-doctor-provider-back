from contextlib import asynccontextmanager

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # 시작 시: DB 연결 확인
    import structlog

    from app.infra.db.cosmos import CosmosDB

    logger = structlog.get_logger()
    try:
        CosmosDB.validate_connection()
    except Exception:
        import sys

        logger.critical("Could not connect to Cosmos DB. Exiting...")
        sys.exit(1)

    yield
    # 종료 시: DB 커넥션 정리
    from app.infra.db.cosmos import CosmosDB

    CosmosDB.close()


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
