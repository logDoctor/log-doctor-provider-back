import structlog
from azure.cosmos.aio import CosmosClient
from azure.identity.aio import DefaultAzureCredential

from app.core.config import settings

logger = structlog.get_logger()


class CosmosDB:
    _client: CosmosClient | None = None
    _database = None

    @classmethod
    def get_client(cls) -> CosmosClient:
        if cls._client is None:
            # 설정에 따라 Managed Identity 적용
            credential = DefaultAzureCredential()
            connection_verify = not settings.AZURE_COSMOS_DISABLE_SSL

            cls._client = CosmosClient(
                settings.COSMOS_ENDPOINT,
                credential=credential,
                connection_verify=connection_verify,
            )
        return cls._client

    @classmethod
    def get_database(cls):
        if cls._database is None:
            client = cls.get_client()
            cls._database = client.get_database_client(settings.COSMOS_DATABASE)
        return cls._database

    @classmethod
    def get_container(cls, container_name: str):
        database = cls.get_database()
        return database.get_container_client(container_name)

    @classmethod
    async def close(cls):  # 비동기 종료
        if cls._client:
            await cls._client.close()
            cls._client = None
            cls._database = None

    @classmethod
    async def validate_connection(cls):
        """실제 DB에 접속하여 연결이 유효한지 비동기로 검증합니다."""
        try:
            client = cls.get_client()
            # 비동기 클라이언트의 데이터베이스 목록 조회를 통해 연결 확인
            async for _ in client.list_databases():
                break
            logger.info("✅ Successfully connected to Cosmos DB")
        except Exception as e:
            logger.error("❌ Failed to connect to Cosmos DB", error=str(e))
            raise


def get_container(container_name: str):
    return CosmosDB.get_container(container_name)
