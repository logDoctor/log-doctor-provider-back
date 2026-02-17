from fastapi import APIRouter
from fastapi_restful.cbv import cbv

router = APIRouter(prefix="/licenses", tags=["License"])


@cbv(router)
class LicenseRouter:
    @router.get("/current")
    async def get_current_license(self):
        return {"message": "Current license placeholder"}
