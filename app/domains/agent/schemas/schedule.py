from pydantic import BaseModel, ConfigDict, field_validator

from app.core.cron import CronHelper


class ScheduleConfigurationItem(BaseModel):
    inspection_codes: list[str]
    resource_groups: list[dict] | None = None


class CreateScheduleRequest(BaseModel):
    enabled: bool = True
    cron_expression: str
    timezone: str = "UTC"
    language: str = "ko"
    configurations: list[ScheduleConfigurationItem]

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        if not CronHelper.is_valid(v):
            raise ValueError(f"Invalid cron expression: '{v}'")
        return v

    @field_validator("configurations")
    @classmethod
    def validate_configurations(cls, v: list) -> list:
        if not v:
            raise ValueError("At least one configuration is required")
        return v


class UpdateScheduleRequest(BaseModel):
    enabled: bool | None = None
    cron_expression: str | None = None
    timezone: str | None = None
    language: str | None = None
    configurations: list[ScheduleConfigurationItem] | None = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
        if v is not None and not CronHelper.is_valid(v):
            raise ValueError(f"Invalid cron expression: '{v}'")
        return v


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    enabled: bool
    cron_expression: str
    timezone: str
    language: str
    configurations: list[dict]
    last_run_at: str | None
    next_run_at: str | None
    created_at: str
    updated_at: str
    created_by: str


class ScheduleListResponse(BaseModel):
    items: list[ScheduleResponse]


class TriggerScheduledRunResponse(BaseModel):
    triggered: bool
    report_id: str | None = None
    schedule_id: str | None = None
    configurations: list[dict] | None = None
    language: str | None = None
