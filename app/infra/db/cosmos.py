from functools import wraps

import structlog
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential

from app.core.config import settings

logger = structlog.get_logger()


class CosmosDB:
    _instance = None
    _client = None
    _database = None
    _containers = {}

    @classmethod
    async def get_client(cls) -> CosmosClient:
        if cls._client is None:
            logger.info(
                "Initializing async Cosmos client", endpoint=settings.COSMOS_ENDPOINT
            )
            # SSL 비활성화를 위한 전송 설정
            connection_verify = not settings.AZURE_COSMOS_DISABLE_SSL

            # 에뮬레이터(http)인 경우 또는 키가 명시된 경우 키 기반 인증 사용
            if settings.COSMOS_KEY:
                credential = settings.COSMOS_KEY
            elif settings.COSMOS_ENDPOINT.startswith("http://"):
                # Cosmos DB 에뮬레이터의 기본 마스터 키
                credential = "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
            else:
                # 설정에 따라 Managed Identity (DefaultAzureCredential) 또는 키를 사용합니다.
                # 로컬 에뮬레이터에서는 키나 인증 비활성화가 필요할 수 있으며, DefaultAzureCredential 오류를 방지합니다.
                # 하지만 Python SDK의 `credential` 인자는 특정 자격 증명을 받거나 키가 제공될 경우 키를 사용합니다.
                # 로컬 에뮬레이터와 `DefaultAzureCredential` 조합은 까다로울 수 있습니다.
                # 이 "mock" 설정에서는 단순함을 위해 자격 증명을 유지하지만 제한 사항에 유의하십시오.
                credential = DefaultAzureCredential()

            cls._client = CosmosClient(
                settings.COSMOS_ENDPOINT,
                credential=credential,
                connection_verify=connection_verify,
                # Docker 환경에서 에뮬레이터가 127.0.0.1로 리다이렉트하는 것을 방지
                enable_endpoint_discovery=False,
            )
        return cls._client

    @classmethod
    async def get_database(cls):
        if cls._database is None:
            client = await cls.get_client()
            cls._database = client.get_database_client(settings.COSMOS_DATABASE)
        return cls._database

    @classmethod
    async def get_container(cls, container_name: str):
        if container_name not in cls._containers:
            database = await cls.get_database()
            cls._containers[container_name] = database.get_container_client(
                container_name
            )
        return cls._containers[container_name]

    @classmethod
    async def validate_connection(cls):
        """실제 DB에 접속하여 연결이 유효한지 검증합니다."""
        try:
            client = await cls.get_client()
            # 데이터베이스 목록을 조회하여 연결 상태를 확인
            async for _ in client.list_databases():
                break
            logger.info("Successfully connected to Cosmos DB")
        except Exception as e:
            logger.error("Failed to connect to Cosmos DB", error=str(e))
            raise

    @classmethod
    async def close(cls):
        """커넥션을 닫고 클라이언트를 정리합니다."""
        if cls._client:
            await cls._client.close()
            cls._client = None
            cls._database = None


async def get_container(container_name: str):
    """컨테이너 클라이언트를 가져오기 위한 의존성 주입 도우미"""
    return await CosmosDB.get_container(container_name)


def cosmos_error_handler(func=None, *, map_to=None):
    """
    Cosmos DB 관련 예외를 처리하고 결과를 도메인 엔티티로 자동 맵핑하는 AOP 데코레이터.
    사용법: @cosmos_error_handler or @cosmos_error_handler(map_to=Agent)
    """

    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            try:
                result = await f(*args, **kwargs)
                # 🛡️ [FIX] 결과가 튜플(list_agents 등)인 경우 하위 항목에 대해 개별 맵핑을 수행하거나
                # 또는 레포지토리 구현체에서 직접 맵핑하도록 유도하기 위해 tuple인 경우 맵핑 스킵
                if (
                    result
                    and map_to
                    and hasattr(map_to, "from_dict")
                    and not isinstance(result, tuple)
                ):
                    if isinstance(result, list):
                        return [map_to.from_dict(item) for item in result]
                    return map_to.from_dict(result)
                return result
            except CosmosResourceNotFoundError:
                if f.__name__.startswith(("get_", "read_")):
                    return None
                elif f.__name__.startswith(("list_", "query_")):
                    return []
                raise
            except Exception as e:
                logger.error(
                    f"Cosmos DB Error in {f.__name__}",
                    error=str(e),
                    func=f.__name__,
                )
                raise

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def cosmos_repository(map_to=None):
    """
    클래스 레벨의 AOP 데코레이터.
    클래스 내의 모든 퍼블릭 메서드(언더스코어로 시작하지 않는 호출 가능한 속성)에
    @cosmos_error_handler(map_to=map_to)를 자동으로 적용합니다.
    """

    def decorator(cls):
        for name, attr in cls.__dict__.items():
            if callable(attr) and not name.startswith("_"):
                # 이미 데코레이터가 적용되어 있을 수 있으므로 체크하거나 덮어씌움
                setattr(cls, name, cosmos_error_handler(map_to=map_to)(attr))
        return cls

    return decorator
