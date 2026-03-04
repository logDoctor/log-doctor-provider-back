from collections.abc import Callable
from typing import Any

from fastapi import APIRouter as FastAPIRouter
from fastapi.routing import APIRoute


class ExcludeNoneRoute(APIRoute):
    """
    모든 엔드포인트에서 기본적으로 response_model_exclude_none=True를 적용하는 커스텀 라우트 클래스입니다.
    """

    def __init__(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        # 명시적으로 설정되지 않은 경우에만 True로 설정
        if "response_model_exclude_none" not in kwargs:
            kwargs["response_model_exclude_none"] = True
        super().__init__(path, endpoint, **kwargs)


class APIRouter(FastAPIRouter):
    """
    프로젝트 표준 APIRouter 클래스입니다.
    기본적으로 ExcludeNoneRoute를 route_class로 사용하여 모든 응답에서 None 값을 제외합니다.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "route_class" not in kwargs:
            kwargs["route_class"] = ExcludeNoneRoute
        super().__init__(*args, **kwargs)
