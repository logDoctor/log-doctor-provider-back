from pydantic import BaseModel


class SubscriptionItem(BaseModel):
    subscription_id: str
    display_name: str


class SubscriptionListResponse(BaseModel):
    subscriptions: list[SubscriptionItem]


class SubscriptionSetupResponse(BaseModel):
    bicep_url: str
    parameters: dict
    portal_link: str
    has_deployment_permission: bool = True
    reason: str | None = None
