from fastapi_restful.cbv import cbv

from app.core.routing import APIRouter

router = APIRouter(prefix="/reports", tags=["Report"])


@cbv(router)
class ReportRouter:
    @router.get("/weekly")
    async def get_weekly_report(self):
        return {"message": "Weekly report placeholder"}
