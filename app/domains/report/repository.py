from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from .models import Report


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
