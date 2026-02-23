import asyncio
import os
from datetime import UTC

import structlog
from azure.cosmos.aio import CosmosClient
from azure.cosmos.exceptions import CosmosResourceExistsError

# 환경 변수 또는 로컬 설정을 기본값으로 사용
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "http://localhost:8081")
COSMOS_KEY = os.getenv(
    "COSMOS_KEY",
    "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==",
)
DATABASE_NAME = os.getenv("COSMOS_DATABASE", "log-doctor-db")

# 테스트용 고정 테넌트 ID
TEST_TENANT_ID = "ccdcba04-0a62-4e96-9964-dc1fc61279f8"

# 컨테이너 정의 (이름, 파티션 키)
CONTAINERS = [
    {"id": "tenants", "partition_key": "/tenant_id"},
    {"id": "agents", "partition_key": "/tenant_id"},
    {"id": "packages", "partition_key": "/partitionKey"},
]

logger = structlog.get_logger()


async def setup_db():
    client = CosmosClient(
        COSMOS_ENDPOINT,
        credential=COSMOS_KEY,
        connection_verify=False,
        enable_endpoint_discovery=False,
    )

    try:
        # 1. 데이터베이스 생성
        logger.info(f"Creating database: {DATABASE_NAME}")
        try:
            database = await client.create_database_if_not_exists(id=DATABASE_NAME)
            logger.info("Database ready")
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            return

        # 2. 컨테이너 생성 및 초기 데이터 삽입
        for container_config in CONTAINERS:
            c_id = container_config["id"]
            p_key = container_config["partition_key"]

            logger.info(f"Creating container: {c_id} (Partition Key: {p_key})")
            try:
                container = await database.create_container_if_not_exists(
                    id=c_id, partition_key={"paths": [p_key], "kind": "Hash"}
                )
                logger.info(f"Container '{c_id}' ready")

                # 3. 테스트용 테넌트 데이터 삽입 (tenants 컨테이너인 경우)
                if c_id == "tenants":
                    from datetime import datetime

                    test_tenant = {
                        "id": TEST_TENANT_ID,
                        "tenant_id": TEST_TENANT_ID,
                        "name": "Test Tenant",
                        "is_active": True,
                        "created_at": datetime.now(UTC).isoformat(),
                    }
                    await container.upsert_item(test_tenant)
                    logger.info(f"Added test tenant record: {TEST_TENANT_ID}")

            except CosmosResourceExistsError:
                logger.info(f"Container '{c_id}' already exists")
            except Exception as e:
                logger.error(f"Failed to create container {c_id}: {e}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(setup_db())
