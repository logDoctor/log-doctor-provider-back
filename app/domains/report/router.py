from fastapi import Depends
from fastapi_restful.cbv import cbv

from app.core.auth.guards import get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import get_create_report_use_case
from .schemas import CreateReportRequest, CreateReportResponse
from .usecases.create_report_use_case import CreateReportUseCase

router = APIRouter(prefix="/reports", tags=["Report"])


@cbv(router)
class ReportRouter:
    @router.post("/", response_model=CreateReportResponse)
    async def create_report(
        self,
        request: CreateReportRequest,
        identity: Identity = Depends(get_current_identity),
        use_case: CreateReportUseCase = Depends(get_create_report_use_case),
    ):
        """새로운 분석 리포트 생성을 요청합니다. (에이전트 분석 트리거)"""
        return await use_case.execute(
            identity=identity,
            request=request,
        )
