from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter


class CronHelper:
    """
    Cron 표현식을 처리하고 다음 실행 시점을 계산하는 유틸리티입니다.
    외부 라이브러리(croniter)에 대한 의존성을 격리합니다.
    """

    @staticmethod
    def _resolve_tz(tz: str) -> ZoneInfo:
        try:
            return ZoneInfo(tz)
        except (ZoneInfoNotFoundError, KeyError):
            return ZoneInfo("UTC")

    @staticmethod
    def get_next_run(schedule: str, base_time: datetime, tz: str = "UTC") -> datetime:
        """
        기준 시간(base_time)으로부터 Cron 스케줄 상의 다음 실행 시점을 반환합니다.
        tz가 지정된 경우 해당 시간대 기준으로 계산 후 UTC로 반환합니다.
        """
        tz_info = CronHelper._resolve_tz(tz)
        base_local = base_time.astimezone(tz_info)
        iter = croniter(schedule, base_local)
        next_local = iter.get_next(datetime)
        if next_local.tzinfo is None:
            next_local = next_local.replace(tzinfo=tz_info)
        return next_local.astimezone(timezone.utc)

    @staticmethod
    def is_time_to_run(
        schedule: str,
        last_run: datetime,
        current_time: datetime,
        tz: str = "UTC",
    ) -> bool:
        """
        마지막 실행 시간과 현재 시간을 비교하여 스케줄상 실행 시점이 되었는지 확인합니다.
        tz가 지정된 경우 해당 시간대 기준으로 계산합니다.
        """
        tz_info = CronHelper._resolve_tz(tz)
        last_run_local = last_run.astimezone(tz_info)
        iter = croniter(schedule, last_run_local)
        next_local = iter.get_next(datetime)
        if next_local.tzinfo is None:
            next_local = next_local.replace(tzinfo=tz_info)
        next_utc = next_local.astimezone(timezone.utc)
        current_utc = current_time.astimezone(timezone.utc)
        return current_utc >= next_utc

    @staticmethod
    def is_valid(schedule: str) -> bool:
        """Cron 표현식 유효성을 검증합니다."""
        return croniter.is_valid(schedule)
