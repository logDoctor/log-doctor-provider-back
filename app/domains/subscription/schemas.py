from pydantic import BaseModel


class SubscriptionItem(BaseModel):
    subscription_id: str
    display_name: str


class SubscriptionListResponse(BaseModel):
    subscriptions: list[SubscriptionItem]
