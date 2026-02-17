from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantResponse(BaseModel):
    tenant_id: str
    is_registered: bool
    is_agent_active: bool
    registered_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
