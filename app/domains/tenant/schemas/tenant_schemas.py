from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class PrivilegedAccountRequest(BaseModel):
    email: str
    user_id: str | None = None


class PrivilegedAccountResponse(BaseModel):
    email: str
    user_id: str




class TeamsInfoPayload(BaseModel):
    team_id: str | None = None
    channel_id: str | None = None
    service_url: str | None = None


class RegisterTenantRequest(BaseModel):
    privileged_accounts: list[PrivilegedAccountRequest] = []
    teams_info: TeamsInfoPayload | None = None

    @field_validator("privileged_accounts", mode="before")
    @classmethod
    def convert_strings_to_dicts(cls, v):
        if not v:
            return v
        return [
            {"email": item, "user_id": ""} if isinstance(item, str) else item
            for item in v
        ]


class RegisterTenantResponse(BaseModel):
    tenant_id: str
    registered_at: datetime | None = None
    privileged_accounts: list[PrivilegedAccountResponse] = []
    teams_info: TeamsInfoPayload | None = None
    model_config = ConfigDict(from_attributes=True)


class UpdateTenantRequest(BaseModel):
    privileged_accounts: list[PrivilegedAccountRequest] | None = None
    teams_info: TeamsInfoPayload | None = None

    @field_validator("privileged_accounts", mode="before")
    @classmethod
    def convert_strings_to_dicts(cls, v):
        if not v:
            return v
        return [
            {"email": item, "user_id": ""} if isinstance(item, str) else item
            for item in v
        ]


class UpdateTenantResponse(BaseModel):
    tenant_id: str
    registered_at: datetime | None = None
    privileged_accounts: list[PrivilegedAccountResponse] = []
    teams_info: TeamsInfoPayload | None = None
    model_config = ConfigDict(from_attributes=True)


class GetTenantStatusResponse(BaseModel):
    tenant_id: str
    registered_at: datetime | None = None
    privileged_accounts: list[PrivilegedAccountResponse] = []
    teams_info: TeamsInfoPayload | None = None
    model_config = ConfigDict(from_attributes=True)
