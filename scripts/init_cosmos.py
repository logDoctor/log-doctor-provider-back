import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가하여 app 모듈을 임포트할 수 있게 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infra.db.cosmos import CosmosDB
from app.core.config import settings

def init_db():
    print(f"Initializing Cosmos DB Emulator: {settings.COSMOS_ENDPOINT}")
    client = CosmosDB.get_client()
    
    # 1. Database 생성 (없으면)
    db_name = settings.COSMOS_DATABASE
    print(f"Creating Database: {db_name}")
    db = client.create_database_if_not_exists(id=db_name)
    
    # 2. Containers 생성 (없으면)
    # tenants 컨테이너 생성 (파티션 키: /id)
    print("Creating Container: tenants")
    db.create_container_if_not_exists(
        id="tenants",
        partition_key={"paths": ["/id"], "kind": "Hash"}
    )
    
    # subscription 컨테이너 생성 (필요할 수 있으므로 추가, 파티션 키: /tenant_id)
    print("Creating Container: subscriptions")
    db.create_container_if_not_exists(
        id="subscriptions",
        partition_key={"paths": ["/tenant_id"], "kind": "Hash"}
    )
    
    # users 컨테이너 생성 (파티션 키: /tenant_id)
    print("Creating Container: users")
    db.create_container_if_not_exists(
        id="users",
        partition_key={"paths": ["/tenant_id"], "kind": "Hash"}
    )
    
    print("Database initialization completed successfully.")

if __name__ == "__main__":
    init_db()
