from fastapi import Depends
from fastapi_restful.cbv import cbv

from app.core.auth.guards import get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

from .dependencies import (
    get_create_report_use_case,
    get_get_report_use_case,
    get_list_diagnoses_by_report_use_case,
    get_list_reports_use_case,
    get_receive_diagnoses_use_case,
    get_update_diagnosis_resolution_use_case,
    get_update_report_status_use_case,
)
from .schemas import (
    AddDiagnosesRequest,
    CreateReportRequest,
    CreateReportResponse,
    DiagnosisSchema,
    ReportListResponse,
    ReportSchema,
    ReportUpdateSchema,
    UpdateDiagnosisResolutionRequest,
)
from .usecases import (
    CreateReportUseCase,
    GetReportUseCase,
    ListDiagnosesByReportUseCase,
    ListReportsUseCase,
    ReceiveDiagnosesUseCase,
    UpdateDiagnosisResolutionUseCase,
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

    @router.get("/", response_model=ReportListResponse)
    async def list_reports(
        self,
        agent_id: str,
        is_initial: bool | None = None,
        cursor: str | None = None,
        limit: int = 20,
        identity: Identity = Depends(get_current_identity),
        use_case: ListReportsUseCase = Depends(get_list_reports_use_case),
    ):
        """조건에 맞는 리포트 목록을 조회합니다. (페이지네이션 지원)"""
        return await use_case.execute(
            identity=identity,
            agent_id=agent_id,
            is_initial=is_initial,
            cursor=cursor,
            limit=limit,
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

    @router.get("/{report_id}/diagnoses", response_model=list[DiagnosisSchema])
    async def list_diagnoses(
        self,
        report_id: str,
        resource_group: str | None = None,
        identity: Identity = Depends(get_current_identity),
        use_case: ListDiagnosesByReportUseCase = Depends(
            get_list_diagnoses_by_report_use_case
        ),
    ):
        """특정 리포트의 상세 진단 항목들을 조회합니다. (리소스 그룹 필터링 지원)"""
        return await use_case.execute(
            tenant_id=identity.tenant_id,
            report_id=report_id,
            resource_group=resource_group,
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
            tenant_id=request.tenant_id,
            status=request.status,
            error=request.error,
        )

        return {"status": "success"}

    @router.patch("/{report_id}/diagnoses/{diagnosis_id}")
    async def update_diagnosis_resolution(
        self,
        report_id: str,
        diagnosis_id: str,
        request: UpdateDiagnosisResolutionRequest,
        identity: Identity = Depends(get_current_identity),
        use_case: UpdateDiagnosisResolutionUseCase = Depends(
            get_update_diagnosis_resolution_use_case
        ),
    ):
        """특정 진단 항목의 해결 상태(is_resolved)를 업데이트합니다."""
        await use_case.execute(
            tenant_id=identity.tenant_id,
            diagnosis_id=diagnosis_id,
            is_resolved=request.is_resolved,
        )

        return {"status": "success"}
