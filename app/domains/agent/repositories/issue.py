from abc import ABC, abstractmethod

from azure.cosmos.aio import ContainerProxy

from app.infra.db.cosmos import cosmos_repository

from ..models import AgentIssue


# 1. Interface (AgentIssue)
class AgentIssueRepository(ABC):
    @abstractmethod
    async def create_issue(self, issue: AgentIssue) -> AgentIssue:
        pass

    @abstractmethod
    async def create_issues(self, issues: list[AgentIssue]) -> list[AgentIssue]:
        pass


# 2. Implementation (Cosmos - AgentIssue)
@cosmos_repository(map_to=AgentIssue)
class AzureAgentIssueRepository(AgentIssueRepository):
    def __init__(self, container: ContainerProxy):
        self.container = container

    async def create_issue(self, issue: AgentIssue) -> AgentIssue:
        # CosmosDB 저장
        await self.container.upsert_item(issue.to_dict())
        return issue

    async def create_issues(self, issues: list[AgentIssue]) -> list[AgentIssue]:
        if not issues:
            return []

        partition_key = issues[0].tenant_id
        batch_operations = []
        for issue in issues:
            batch_operations.append(("upsert", (issue.to_dict(),)))

        await self.container.execute_item_batch(
            batch_operations=batch_operations, partition_key=partition_key
        )
        return issues
