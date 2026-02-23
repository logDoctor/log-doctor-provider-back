from datetime import datetime

from croniter import croniter


class CronHelper:
    """
    Cron 표현식을 처리하고 다음 실행 시점을 계산하는 유틸리티입니다.
    외부 라이브러리(croniter)에 대한 의존성을 격리합니다.
    """

    @staticmethod
    def get_next_run(schedule: str, base_time: datetime) -> datetime:
        """
        기준 시간(base_time)으로부터 Cron 스케줄 상의 다음 실행 시점을 반환합니다.
        """
        iter = croniter(schedule, base_time)
        return iter.get_next(datetime)

    @staticmethod
    def is_time_to_run(
        schedule: str, last_run: datetime, current_time: datetime
    ) -> bool:
        """
        마지막 실행 시간과 현재 시간을 비교하여 스케줄상 실행 시점이 되었는지 확인합니다.
        """
        iter = croniter(schedule, last_run)
        next_run = iter.get_next(datetime)
        return current_time >= next_run
