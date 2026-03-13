from fastapi import Depends
from fastapi_restful.cbv import cbv

from app.core.auth.guards import get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import (
    get_create_report_use_case,
    get_get_report_use_case,
    get_receive_diagnoses_use_case,
    get_update_report_status_use_case,
)
from .schemas import (
    AddDiagnosesRequest,
    CreateReportRequest,
    CreateReportResponse,
    ReportSchema,
    ReportUpdateSchema,
)
from .usecases import (
    CreateReportUseCase,
    GetReportUseCase,
    ReceiveDiagnosesUseCase,
    UpdateReportStatusUseCase,
)

router = APIRouter(tags=["Report"])


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

    @router.get("/{report_id}", response_model=ReportSchema)
    async def get_report(
        self,
        report_id: str,
        wait: bool = False,
        identity: Identity = Depends(get_current_identity),
        use_case: GetReportUseCase = Depends(get_get_report_use_case),
    ):
        """리포트의 현재 상태를 조회합니다. wait=true 이면 완료될 때까지 대기(Long-polling)합니다."""
        return await use_case.execute(
            identity=identity,
            report_id=report_id,
            wait_for_completion=wait,
        )

    @router.post("/{report_id}/diagnoses")
    async def receive_diagnoses(
        self,
        report_id: str,
        request: AddDiagnosesRequest,
        identity: Identity = Depends(get_current_identity),
        use_case: ReceiveDiagnosesUseCase = Depends(get_receive_diagnoses_use_case),
    ):
        """에이전트로부터 진단 항목들을 수집합니다."""
        await use_case.execute(
            report_id=report_id,
            tenant_id=identity.tenant_id,
            request=request,
        )

        return {"status": "success"}

    @router.patch("/{report_id}")
    async def update_report_status(
        self,
        report_id: str,
        request: ReportUpdateSchema,
        identity: Identity = Depends(get_current_identity),
        use_case: UpdateReportStatusUseCase = Depends(
            get_update_report_status_use_case
        ),
    ):
        """리포트의 상태를 업데이트하고 분석을 마감합니다."""
        await use_case.execute(
            report_id=report_id,
            tenant_id=identity.tenant_id,
            status=request.status,
            error=request.error,
        )

        return {"status": "success"}
