from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RegisterTenantRequest(BaseModel):
    privileged_accounts: list[str] = []


class UpdateTenantRequest(BaseModel):
    privileged_accounts: list[str] | None = None


class GetTenantStatusResponse(BaseModel):
    tenant_id: str
    registered_at: datetime | None = None
    privileged_accounts: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class RegisterTenantResponse(BaseModel):
    tenant_id: str
    registered_at: datetime | None = None
    privileged_accounts: list[str] = []

    model_config = ConfigDict(from_attributes=True)
