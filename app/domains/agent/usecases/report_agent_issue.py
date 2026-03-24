from app.domains.agent.models import AgentIssue
from app.domains.agent.repository import AgentIssueRepository
from app.domains.agent.schemas import AgentIssueCreate


class ReportAgentIssueUseCase:
    def __init__(self, repository: AgentIssueRepository):
        self.repository = repository

    async def execute(
        self, tenant_id: str, agent_id: str, request: list[AgentIssueCreate]
    ) -> list[AgentIssue]:
        issues = []
        for req in request:
            issues.append(
                AgentIssue.create(
                    tenant_id=tenant_id or req.tenant_id or "unknown",
                    agent_id=agent_id,
                    issue_type=req.issue_type,
                    message=req.message,
                    raw_data=req.raw_data,
                )
            )

        return await self.repository.create_issues(issues)
