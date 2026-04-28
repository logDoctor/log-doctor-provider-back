from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from .models.schedule import Schedule


class ScheduleRepository(ABC):
    @abstractmethod
    async def create(self, schedule: Schedule) -> Schedule:
        pass

    @abstractmethod
    async def get_by_id(self, agent_id: str, schedule_id: str) -> Schedule | None:
        pass

    @abstractmethod
    async def list_by_agent(self, tenant_id: str, agent_id: str) -> list[Schedule]:
        pass

    @abstractmethod
    async def get_enabled_by_agent(
        self, tenant_id: str, agent_id: str
    ) -> list[Schedule]:
        pass

    @abstractmethod
    async def count_by_agent(self, tenant_id: str, agent_id: str) -> int:
        pass

    @abstractmethod
    async def update(self, schedule: Schedule) -> Schedule:
        pass

    @abstractmethod
    async def delete(self, agent_id: str, schedule_id: str) -> None:
        pass

    @abstractmethod
    async def disable_by_agent(self, agent_id: str) -> None:
        """에이전트와 연관된 모든 스케줄을 비활성화합니다."""
        pass


@cosmos_repository(map_to=Schedule)
class AzureScheduleRepository(ScheduleRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def create(self, schedule: Schedule) -> Schedule:
        return await self.container.create_item(schedule.to_dict())

    async def get_by_id(self, agent_id: str, schedule_id: str) -> Schedule | None:
        return await self.container.read_item(
            item=schedule_id, partition_key=agent_id
        )

    async def list_by_agent(self, tenant_id: str, agent_id: str) -> list[Schedule]:
        query = (
            "SELECT * FROM c WHERE c.tenant_id = @tenant_id AND c.agent_id = @agent_id"
            " ORDER BY c.created_at DESC"
        )
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@agent_id", "value": agent_id},
        ]
        items = []
        async for item in self.container.query_items(
            query=query, parameters=parameters, partition_key=agent_id
        ):
            items.append(item)
        return items

    async def get_enabled_by_agent(
        self, tenant_id: str, agent_id: str
    ) -> list[Schedule]:
        query = (
            "SELECT * FROM c WHERE c.tenant_id = @tenant_id"
            " AND c.agent_id = @agent_id AND c.enabled = true"
        )
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@agent_id", "value": agent_id},
        ]
        items = []
        async for item in self.container.query_items(
            query=query, parameters=parameters, partition_key=agent_id
        ):
            items.append(item)
        return items

    async def count_by_agent(self, tenant_id: str, agent_id: str) -> int:
        query = (
            "SELECT VALUE COUNT(1) FROM c"
            " WHERE c.tenant_id = @tenant_id AND c.agent_id = @agent_id"
        )
        parameters = [
            {"name": "@tenant_id", "value": tenant_id},
            {"name": "@agent_id", "value": agent_id},
        ]
        async for item in self.container.query_items(
            query=query, parameters=parameters, partition_key=agent_id
        ):
            return item
        return 0

    async def update(self, schedule: Schedule) -> Schedule:
        body = schedule.to_dict()
        if schedule._etag:
            from azure.core import MatchConditions
            return await self.container.replace_item(
                item=schedule.id,
                body=body,
                etag=schedule._etag,
                match_condition=MatchConditions.IfNotModified,
            )
        return await self.container.upsert_item(body=body)

    async def delete(self, agent_id: str, schedule_id: str) -> None:
        await self.container.delete_item(item=schedule_id, partition_key=agent_id)

    async def disable_by_agent(self, agent_id: str) -> None:
        # list_by_agent는 tenant_id도 필요하지만 파티션 스캔으로 대체
        query = "SELECT * FROM c WHERE c.agent_id = @agent_id AND c.enabled = true"
        parameters = [{"name": "@agent_id", "value": agent_id}]
        enabled = []
        async for item in self.container.query_items(
            query=query, parameters=parameters, partition_key=agent_id
        ):
            enabled.append(item)

        if not enabled:
            return

        for s in enabled:
            s["enabled"] = False

        batch = [("upsert", s, {}) for s in enabled]
        await self.container.execute_item_batch(
            batch_operations=batch,
            partition_key=agent_id,
        )
