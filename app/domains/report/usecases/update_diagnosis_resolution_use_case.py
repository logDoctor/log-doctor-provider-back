import asyncio
from datetime import UTC, datetime
from typing import Any

from app.core.exceptions import NotFoundException
from app.domains.report.repositories import DiagnosisRepository, ReportRepository


class UpdateDiagnosisResolutionUseCase:
    def __init__(
        self,
        diagnosis_repository: DiagnosisRepository,
        report_repository: ReportRepository,
        insight_publisher: Any = None,  # DI 추가
    ):
        self.diagnosis_repository = diagnosis_repository
        self.report_repository = report_repository
        self.insight_publisher = insight_publisher

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

        if diagnosis.is_resolved == is_resolved:
            return  # 상태 변화 없음

        diagnosis.is_resolved = is_resolved
        diagnosis.updated_at = datetime.now(UTC).isoformat()
        await self.diagnosis_repository.update_diagnosis(diagnosis)

        # 리포트 요약(summary) 업데이트 (낙관적 락 재시도 로직 적용)
        max_retries = 3
        for i in range(max_retries):
            try:
                report = await self.report_repository.get_by_id(
                    tenant_id, diagnosis.report_id
                )
                if not report:
                    break

                if report.summary is None:
                    report.summary = {}

                current_resolved = report.summary.get("resolved_diagnosis_count", 0)
                if is_resolved:
                    report.summary["resolved_diagnosis_count"] = current_resolved + 1
                else:
                    report.summary["resolved_diagnosis_count"] = max(
                        0, current_resolved - 1
                    )

                await self.report_repository.update_report(report)
                break  # 업데이트 성공 시 루프 탈출

            except Exception as e:
                # CosmosHttpResponseError 계열인 경우 status_code 검사
                if (
                    hasattr(e, "status_code") and e.status_code == 412
                ):  # Precondition Failed (ETag 불일치)
                    if i == max_retries - 1:
                        raise  # 재시도 횟수 초과 시 최종 에러 발생
                    await asyncio.sleep(0.1)  # 짧은 대기 후 재시도
                else:
                    raise  # 412 이외의 심각한 오류는 즉시 던짐

        if self.insight_publisher:
            try:
                # 비동기로 이벤트 발행
                asyncio.create_task(
                    self.insight_publisher.publish(
                        event_type="diagnosis_resolved",
                        tenant_id=tenant_id,
                        agent_id=report.agent_id,
                        report_id=diagnosis.report_id,
                        diagnosis_id=diagnosis_id,
                        is_resolved=is_resolved,
                    )
                )
            except Exception as e:
                # 이벤트 발행 실패가 비즈니스 로직에 영향을 주지 않도록 로깅만 수행
                from app.core.logging import get_logger

                get_logger("update_diagnosis_resolution").error(
                    "failed_to_publish_insight_event", error=str(e)
                )
