from enum import Enum
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


class PeriodType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    TOTAL = "total"


# 컨테이너 매핑
PERIOD_CONTAINER_MAP = {
    PeriodType.DAILY: "insights_daily",
    PeriodType.WEEKLY: "insights_weekly",
    PeriodType.MONTHLY: "insights_monthly",
    PeriodType.TOTAL: "insights_total",
}
