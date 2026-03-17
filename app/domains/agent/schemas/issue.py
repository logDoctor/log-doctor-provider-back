from pydantic import BaseModel

class AgentIssueCreate(BaseModel):
    tenant_id: str | None = None
    issue_type: str
    message: str
    raw_data: str | None = None
