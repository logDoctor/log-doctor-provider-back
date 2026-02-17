from fastapi import APIRouter

from app.domains.agent.router import router as agent_router
from app.domains.license.router import router as license_router
from app.domains.report.router import router as report_router
from app.domains.subscription.router import router as subscription_router
from app.domains.tenant.router import router as tenant_router

v1_router = APIRouter()

v1_router.include_router(tenant_router)
v1_router.include_router(subscription_router)
v1_router.include_router(agent_router)
v1_router.include_router(report_router)
v1_router.include_router(license_router)
