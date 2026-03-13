from datetime import UTC, datetime

from app.core.exceptions import NotFoundException
from app.domains.report.repository import DiagnosisRepository

class UpdateDiagnosisResolutionUseCase:
    def __init__(self, diagnosis_repository: DiagnosisRepository):
        self.diagnosis_repository = diagnosis_repository

    async def execute(
        self,
        tenant_id: str,
        diagnosis_id: str,
        is_resolved: bool,
    ) -> None:
        """진단 항목의 해결 상태(is_resolved)를 업데이트합니다."""
        diagnosis = await self.diagnosis_repository.get_by_id(tenant_id, diagnosis_id)
        if not diagnosis:
            raise NotFoundException(f"Diagnosis not found: {diagnosis_id}")

        diagnosis.is_resolved = is_resolved
        diagnosis.updated_at = datetime.now(UTC).isoformat()
        await self.diagnosis_repository.update_diagnosis(diagnosis)
