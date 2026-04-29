from app.domains.report.models import Diagnosis
from app.domains.report.repositories import DiagnosisRepository
from app.domains.report.schemas import AddDiagnosesRequest


class ReceiveDiagnosesUseCase:
    """에이전트로부터 진단 항목들을 수신하여 벌크 저장하는 UseCase"""

    def __init__(self, diagnosis_repository: DiagnosisRepository):
        self.diagnosis_repository = diagnosis_repository

    async def execute(
        self, report_id: str, tenant_id: str, request: AddDiagnosesRequest
    ) -> None:
        diagnoses = [
            Diagnosis.create(
                report_id=report_id,
                tenant_id=tenant_id,
                inspection_code=item.inspection_code,
                status=item.status,
                description=item.description,
                resource_id=item.resource_id,
                prescriptions=item.prescriptions,
                resource_group=item.resource_group.model_dump(),
            )
            for item in request.items
        ]

        await self.diagnosis_repository.create_diagnoses(diagnoses)
