import structlog
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential

from app.core.config import settings

logger = structlog.get_logger()


class CosmosDB:
    _instance = None
    _client = None
    _database = None

    @classmethod
    def get_client(cls) -> CosmosClient:
        if cls._client is None:
            # 설정에 따라 Managed Identity (DefaultAzureCredential) 또는 키를 사용합니다.
            # 로컬 에뮬레이터에서는 키나 인증 비활성화가 필요할 수 있으며, DefaultAzureCredential 오류를 방지합니다.

            # SSL 비활성화를 위한 전송 설정
            connection_verify = not settings.AZURE_COSMOS_DISABLE_SSL

            if settings.COSMOS_KEY:
                logger.info("Connecting to Cosmos DB using Primary Key")
                credential = settings.COSMOS_KEY
            else:
                logger.info("Connecting to Cosmos DB using DefaultAzureCredential")
                credential = DefaultAzureCredential()

            cls._client = CosmosClient(
                settings.COSMOS_ENDPOINT,
                credential=credential,
                connection_verify=connection_verify,
                # 에뮬레이터 환경에서 SDK가 127.0.0.1로 라우팅하는 것을 방지
                enable_endpoint_discovery=False if settings.COSMOS_KEY else True,
            )
        return cls._client

    @classmethod
    def get_database(cls):
        if cls._database is None:
            client = cls.get_client()
            cls._database = client.create_database_if_not_exists(id=settings.COSMOS_DATABASE)
        return cls._database

    @classmethod
    def get_container(cls, container_name: str):
        database = cls.get_database()
        return database.get_container_client(container_name)

    @classmethod
    def validate_connection(cls):
        """실제 DB에 접속하여 연결이 유효한지 검증하고 DB를 자동 생성합니다."""
        try:
            client = cls.get_client()
            list(client.list_databases())
            # 시작 시점에 데이터베이스를 자동으로 생성 (에뮬레이터 초기화 용이)
            cls.get_database()
            logger.info(f"Successfully connected to Cosmos DB (Database: {settings.COSMOS_DATABASE})")
        except Exception as e:
            logger.error("Failed to connect to Cosmos DB", error=str(e))
            raise

    @classmethod
    def close(cls):
        """커넥션을 닫고 클라이언트를 정리합니다."""
        if cls._client:
            cls._client.close()
            cls._client = None
            cls._database = None


def get_container(container_name: str):
    """컨테이너 클라이언트를 가져오기 위한 의존성 주입 도우미"""
    return CosmosDB.get_container(container_name)
