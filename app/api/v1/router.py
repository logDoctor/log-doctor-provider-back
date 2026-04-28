from fastapi import APIRouter

from app.api.v1.endpoints.inspection_rules import router as inspection_rules_router
from app.api.v1.endpoints.support import router as support_router
from app.api.v1.endpoints.teams_webhook import router as teams_webhook_router
from app.api.v1.endpoints.template import router as template_router
from app.domains.agent.router import router as agent_router
from app.domains.license.router import router as license_router
from app.domains.notification.router import router as notification_router
from app.domains.package.router import router as package_router
from app.domains.report.router import router as report_router
from app.domains.tenant.router import router as tenant_router

v1_router = APIRouter()

v1_router.include_router(template_router, prefix="/templates")
v1_router.include_router(support_router, prefix="/support")
v1_router.include_router(teams_webhook_router, prefix="/teams/webhook")
v1_router.include_router(tenant_router, prefix="/tenants")
v1_router.include_router(notification_router, prefix="/notifications")
v1_router.include_router(agent_router, prefix="/agents")
v1_router.include_router(report_router, prefix="/reports")
v1_router.include_router(license_router, prefix="/licenses")
v1_router.include_router(package_router, prefix="/packages")
v1_router.include_router(inspection_rules_router, prefix="/inspection-rules")
