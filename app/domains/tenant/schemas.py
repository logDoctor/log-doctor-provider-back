from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------
# 1. 기존 팀 초안 (테넌트 상태 조회용) - 절대 건드리지 않음!
# ---------------------------------------------------------
class TenantResponse(BaseModel):
    tenant_id: str
    is_registered: bool
    is_agent_active: bool
    registered_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

# ---------------------------------------------------------
# 2. 신규 추가 (다이어그램 [Step 2] OBO Flow 구독 목록 조회용)
# ---------------------------------------------------------
class SubscriptionInfo(BaseModel):
    """구독 1개의 정보를 담는 모델"""
    subscription_id: str = Field(..., description="Azure 구독 ID")
    display_name: str = Field(..., description="구독의 표시 이름 (예: LogDoctor Production)")
    state: str = Field(..., description="구독 상태 (예: Enabled)")

class GetSubscriptionsResponse(BaseModel):
    """프론트엔드에 응답할 최종 데이터 (구독 목록 배열)"""
    subscriptions: list[SubscriptionInfo] = Field(..., description="사용자가 접근 가능한 구독 목록")