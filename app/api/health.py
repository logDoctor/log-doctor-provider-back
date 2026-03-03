from app.core.routing import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health/live")
async def liveness_probe():
    """
    서버가 살아있는지 확인합니다 (Liveness Probe).
    컨테이너 오케스트레이터(k8s)가 컨테이너를 재시작해야 할지 결정할 때 사용합니다.
    """
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness_probe():
    """
    서버가 트래픽을 받을 준비가 되었는지 확인합니다 (Readiness Probe).
    DB 연결 등 필수 의존성이 정상인지 체크합니다.
    """
    # TODO: 여기에 DB 핑 체크 추가
    # from app.infra.db.cosmos import get_container
    # check_db_connection()
    return {"status": "ready"}
