from app.infra.db.cosmos import CosmosDB

from .agent import AgentRepository, AzureAgentRepository
from .issue import AgentIssueRepository, AzureAgentIssueRepository
from .schedule import AzureScheduleRepository, ScheduleRepository

__all__ = [
    "AgentRepository",
    "AzureAgentRepository",
    "ScheduleRepository",
    "AzureScheduleRepository",
    "AgentIssueRepository",
    "AzureAgentIssueRepository",
    "get_agent_repository",
    "get_schedule_repository",
    "get_agent_issue_repository",
]


async def get_agent_repository() -> AgentRepository:
    container = await CosmosDB.get_container("agents")
    return AzureAgentRepository(container)


async def get_schedule_repository() -> ScheduleRepository:
    container = await CosmosDB.get_container("schedules")
    return AzureScheduleRepository(container)


async def get_agent_issue_repository() -> AgentIssueRepository:
    container = await CosmosDB.get_container("agent_issues")
    return AzureAgentIssueRepository(container)
