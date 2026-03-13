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
        return await self.container.upsert_item(body=report.to_dict())

    async def list_reports(
        self,
        tenant_id: str,
        agent_id: str,
        is_initial: bool | None = None,
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

        # 최신순 정렬
        query += " ORDER BY c.created_at DESC"

        items_iterable = self.container.query_items(
            query=query,
            parameters=parameters,
            max_item_count=limit,
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
            return Report.from_dict(item)

        return None

class DiagnosisRepository(ABC):
    @abstractmethod
    async def create_diagnoses(self, diagnoses: list[Diagnosis]) -> None:
        """여러 진단 결과를 일괄 저장합니다."""
        pass

    @abstractmethod
    async def list_by_report(self, tenant_id: str, report_id: str) -> list[Diagnosis]:
        """특정 리포트의 모든 진단 항목을 조회합니다."""
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

    async def list_by_report(self, tenant_id: str, report_id: str) -> list[Diagnosis]:
        query = "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.report_id = @report_id"
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@report_id", "value": report_id},
        ]

        items_iterable = self.container.query_items(
            query=query,
            parameters=parameters,
        )

        items = []
        async for item in items_iterable:
            items.append(item)

        return items

    async def get_by_id(self, tenant_id: str, diagnosis_id: str) -> Diagnosis | None:
        try:
            return await self.container.read_item(item=diagnosis_id, partition_key=tenant_id)
        except Exception:
            return None

    async def update_diagnosis(self, diagnosis: Diagnosis) -> Diagnosis:
        return await self.container.upsert_item(body=diagnosis.to_dict())
