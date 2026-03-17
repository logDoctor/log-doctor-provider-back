from app.domains.agent.models import AgentIssue
from app.domains.agent.repository import AgentIssueRepository
from app.domains.agent.schemas import AgentIssueCreate

class ReportAgentIssueUseCase:
    def __init__(self, repository: AgentIssueRepository):
        self.repository = repository

    async def execute(self, tenant_id: str, agent_id: str, request: AgentIssueCreate) -> AgentIssue:
        # Pydantic 모델에서 도메인 모델 생성
        issue = AgentIssue.create(
            tenant_id=tenant_id or request.tenant_id or "unknown",
            agent_id=agent_id,
            issue_type=request.issue_type,
            message=request.message,
            raw_data=request.raw_data
        )
        
        # 레포지토리 저장
        return await self.repository.create_issue(issue)
