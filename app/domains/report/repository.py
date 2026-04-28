import asyncio
from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from .models import Diagnosis, Report


class ReportRepository(ABC):
    @abstractmethod
    async def create_report(self, report: Report) -> Report:
        """새로운 리포트(PENDING)를 생성합니다."""
        pass

    @abstractmethod
    async def get_by_id(self, tenant_id: str, report_id: str) -> Report | None:
        """ID로 리포트를 조회합니다."""
        pass

    @abstractmethod
    async def update_report(self, report: Report) -> Report:
        """리포트의 상태 및 결과 데이터를 업데이트합니다."""
        pass

    @abstractmethod
    async def list_reports(
        self,
        tenant_id: str,
        agent_id: str,
        is_initial: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        resolution_status: str | None = None,
        triggered_by: str | None = None,
        diagnosis_type: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Report], str | None]:
        """조건에 맞는 리포트 목록을 조회합니다. (커서 기반 페이지네이션)"""
        pass

    @abstractmethod
    async def get_initial(self, tenant_id: str, agent_id: str) -> Report | None:
        """에이전트의 초진 리포트를 조회합니다."""
        pass


@cosmos_repository(map_to=Report)
class AzureReportRepository(ReportRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def create_report(self, report: Report) -> Report:
        return await self.container.create_item(report.to_dict())

    async def get_by_id(self, tenant_id: str, report_id: str) -> Report | None:
        return await self.container.read_item(item=report_id, partition_key=tenant_id)

    async def update_report(self, report: Report) -> Report:
        body = report.to_dict()
        if hasattr(report, "_etag") and report._etag:
            from azure.core import MatchConditions
            return await self.container.replace_item(
                item=report.id,
                body=body,
                etag=report._etag,
                match_condition=MatchConditions.IfNotModified
            )
        return await self.container.upsert_item(body=body)

    async def list_reports(
        self,
        tenant_id: str,
        agent_id: str,
        is_initial: bool | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        resolution_status: str | None = None,
        triggered_by: str | None = None,
        diagnosis_type: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[list[Report], str | None]:
        query = "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.agent_id = @agent_id"
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@agent_id", "value": agent_id},
        ]

        if is_initial is not None:
            query += " AND c.is_initial = @is_initial"
            parameters.append({"name": "@is_initial", "value": is_initial})

        if start_date:
            query += " AND c.created_at >= @start_date"
            parameters.append({"name": "@start_date", "value": start_date})

        if end_date:
            query += " AND c.created_at <= @end_date"
            parameters.append({"name": "@end_date", "value": end_date})

        if resolution_status == "HEALTHY":
            query += " AND (IS_DEFINED(c.summary) AND c.summary.detected_diagnosis_count = 0)"
        elif resolution_status == "UNRESOLVED":
            query += " AND (IS_DEFINED(c.summary) AND c.summary.detected_diagnosis_count > 0 AND c.summary.resolved_diagnosis_count < c.summary.detected_diagnosis_count)"
        elif resolution_status == "RESOLVED":
            query += " AND (IS_DEFINED(c.summary) AND c.summary.detected_diagnosis_count > 0 AND c.summary.resolved_diagnosis_count = c.summary.detected_diagnosis_count)"

        if triggered_by:
            query += " AND CONTAINS(LOWER(c.triggered_by), LOWER(@triggered_by))"
            parameters.append({"name": "@triggered_by", "value": triggered_by})

        if diagnosis_type == "ROUTINE":
            query += (
                " AND (NOT IS_DEFINED(c.triggered_by) OR c.triggered_by = null"
                " OR c.triggered_by = 'System' OR STARTSWITH(c.triggered_by, 'scheduled:'))"
            )
        elif diagnosis_type == "MANUAL":
            query += (
                " AND (IS_DEFINED(c.triggered_by) AND c.triggered_by != null"
                " AND c.triggered_by != 'System' AND NOT STARTSWITH(c.triggered_by, 'scheduled:'))"
            )

        # 최신순 정렬
        query += " ORDER BY c.created_at DESC"

        items_iterable = self.container.query_items(
            query=query,
            parameters=parameters,
            max_item_count=limit,
            partition_key=tenant_id
        )

        pages = items_iterable.by_page(continuation_token=cursor)
        items = []
        
        try:
            page = await pages.__anext__()
            async for item in page:
                items.append(Report.from_dict(item))
            next_cursor = pages.continuation_token
        except StopAsyncIteration:
            next_cursor = None

        return items, next_cursor

    async def get_initial(self, tenant_id: str, agent_id: str) -> Report | None:
        query = "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.agent_id = @agent_id AND c.is_initial = true"
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@agent_id", "value": agent_id},
        ]

        items_iterable = self.container.query_items(
            query=query,
            parameters=parameters,
            max_item_count=1,
        )

        async for item in items_iterable:
            return item

        return None

class DiagnosisRepository(ABC):
    @abstractmethod
    async def create_diagnoses(self, diagnoses: list[Diagnosis]) -> None:
        """여러 진단 결과를 일괄 저장합니다."""
        pass

    @abstractmethod
    async def list_by_report(self, tenant_id: str, report_id: str, resource_group: str | None = None) -> list[Diagnosis]:
        """특정 리포트의의 진단 항목을 조회합니다. (리소스 그룹 필터 적용 가능)"""
        pass

    @abstractmethod
    async def get_by_id(self, tenant_id: str, diagnosis_id: str) -> Diagnosis | None:
        """ID로 특정 진단 항목을 조회합니다."""
        pass

    @abstractmethod
    async def update_diagnosis(self, diagnosis: Diagnosis) -> Diagnosis:
        """진단 항목 정보를 업데이트합니다."""
        pass


@cosmos_repository(map_to=Diagnosis)
class AzureDiagnosisRepository(DiagnosisRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def create_diagnoses(self, diagnoses: list[Diagnosis]) -> None:
        if not diagnoses:
            return

        tasks = [self.container.create_item(d.to_dict()) for d in diagnoses]

        await asyncio.gather(*tasks)

    async def list_by_report(self, tenant_id: str, report_id: str, resource_group: str | None = None) -> list[dict]:
        query = "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.report_id = @report_id"
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@report_id", "value": report_id},
        ]

        if resource_group:
            query += " AND CONTAINS(LOWER(c.resource_id), LOWER(@rg_pattern))"
            parameters.append({"name": "@rg_pattern", "value": f"/resourcegroups/{resource_group}/"})

        items_iterable = self.container.query_items(
            query=query,
            parameters=parameters,
            partition_key=report_id
        )

        items = []
        async for item in items_iterable:
            items.append(item)

        return items

    async def get_by_id(self, tenant_id: str, diagnosis_id: str) -> Diagnosis | None:
        query = "SELECT * FROM c WHERE c.id = @diagnosis_id AND c.tenant_id = @tenant_id"
        parameters = [
            {"name": "@diagnosis_id", "value": diagnosis_id},
            {"name": "@tenant_id", "value": tenant_id},
        ]
        items_iterable = self.container.query_items(
            query=query,
            parameters=parameters
        )
        async for item in items_iterable:
            return item
        return None

    async def update_diagnosis(self, diagnosis: Diagnosis) -> Diagnosis:
        return await self.container.upsert_item(body=diagnosis.to_dict())
