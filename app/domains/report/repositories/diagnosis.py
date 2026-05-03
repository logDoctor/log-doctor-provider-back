import asyncio
from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from ..models import Diagnosis


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
            query += " AND (CONTAINS(LOWER(c.resource_id), LOWER(@rg_pattern)) OR LOWER(c.resource_group.name) = LOWER(@rg_name))"
            parameters.append({"name": "@rg_pattern", "value": f"/resourcegroups/{resource_group}/"})
            parameters.append({"name": "@rg_name", "value": resource_group})

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
