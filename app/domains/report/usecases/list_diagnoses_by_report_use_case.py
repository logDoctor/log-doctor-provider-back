from ..repositories import DiagnosisRepository
from ..schemas import DiagnosisSchema


class ListDiagnosesByReportUseCase:
    """특정 리포트의의 상세 진단 항목들을(리소스 그룹 필터 포함) 조회하는 UseCase"""

    def __init__(self, diagnosis_repository: DiagnosisRepository):
        self.diagnosis_repository = diagnosis_repository

    async def execute(
        self, tenant_id: str, report_id: str, resource_group: str | None = None
    ) -> list[DiagnosisSchema]:
        diagnoses = await self.diagnosis_repository.list_by_report(
            tenant_id, report_id, resource_group
        )

        return [DiagnosisSchema.model_validate(d) for d in diagnoses]
