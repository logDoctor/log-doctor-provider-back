from datetime import datetime
from typing import List, Optional

from app.domains.report.models import ReportStatus
from app.domains.report.repositories.diagnosis import DiagnosisRepository
from app.domains.report.repositories.report import ReportRepository

from ..schemas import ActiveRiskDetailSchema, ActiveRisksListResponse


class GetActiveRisksUseCase:
    def __init__(
        self,
        report_repository: ReportRepository,
        diagnosis_repository: DiagnosisRepository,
    ):
        self.report_repository = report_repository
        self.diagnosis_repository = diagnosis_repository

    async def execute(
        self,
        tenant_id: str,
        agent_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> ActiveRisksListResponse:
        # 1. 해결되지 않은 리포트 목록을 가져옵니다.
        # (인사이트 성능을 위해 가장 최신 리포트들 위주로 검색)
        reports, next_cursor = await self.report_repository.list_reports(
            tenant_id=tenant_id,
            agent_id=agent_id,
            resolution_status="UNRESOLVED",
            limit=50,  # 최근 50개 리포트 내에서 리스크 수집
        )

        all_active_risks = []

        # 2. 각 리포트에서 해결되지 않은 진단 항목들을 수집합니다.
        for report in reports:
            if report.status != ReportStatus.COMPLETED:
                continue

            diagnoses = await self.diagnosis_repository.list_by_report(
                tenant_id=tenant_id, report_id=report.id
            )

            for diag_dict in diagnoses:
                # dict인 경우와 객체인 경우를 모두 고려 (Repository 반환 형식이 섞여 있을 수 있음)
                is_resolved = (
                    diag_dict.get("is_resolved", False)
                    if isinstance(diag_dict, dict)
                    else getattr(diag_dict, "is_resolved", False)
                )
                status = (
                    diag_dict.get("status", "")
                    if isinstance(diag_dict, dict)
                    else getattr(diag_dict, "status", "")
                )

                if not is_resolved and status == "DETECTED":
                    risk = ActiveRiskDetailSchema(
                        report_id=report.id,
                        diagnosis_id=diag_dict.get("id")
                        if isinstance(diag_dict, dict)
                        else diag_dict.id,
                        engine_code=diag_dict.get("inspection_code")
                        if isinstance(diag_dict, dict)
                        else diag_dict.inspection_code,
                        title=diag_dict.get("description", "")
                        if isinstance(diag_dict, dict)
                        else diag_dict.description,
                        severity="high",  # 기본값, 필요시 추가 로직 구현
                        created_at=datetime.fromisoformat(
                            diag_dict.get("created_at")
                            if isinstance(diag_dict, dict)
                            else diag_dict.created_at
                        ),
                    )
                    all_active_risks.append(risk)

        # 3. 수동 페이지네이션 (간단한 구현)
        start_idx = int(cursor) if cursor and cursor.isdigit() else 0
        paged_items = all_active_risks[start_idx : start_idx + limit]
        has_more = len(all_active_risks) > (start_idx + limit)

        return ActiveRisksListResponse(
            items=paged_items, total_count=len(all_active_risks), has_more=has_more
        )
