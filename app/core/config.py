from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Authentication Settings
    # AUTH_METHOD: managed_identity | secret | mock
    AUTH_METHOD: str = "managed_identity"

    # Azure AD Settings
    # Managed Identity 사용 시 필요하지 않을 수 있으나, AUTH_METHOD="secret"인 경우 .env에서 주입받습니다.
    CLIENT_ID: str | None = None
    CLIENT_SECRET: str | None = None
    TENANT_ID: str | None = None

    # Cosmos DB Settings
    COSMOS_ENDPOINT: str = "https://mock-cosmos.documents.azure.com:443/"
    COSMOS_KEY: str | None = None
    COSMOS_DATABASE: str = "log-doctor-db"
    AZURE_COSMOS_DISABLE_SSL: bool = False

    # API Settings
    BASE_URL: str = "http://localhost:8000"
    AGENT_PACKAGE_URL: str = (
        "https://github.com/log-doctor/agent/releases/latest/download/dist.zip"
    )
    DOWNLOAD_SECRET_KEY: str = "default-dev-secret-key-for-local-development-only"

    # Storage Settings
    # STORAGE_TYPE: filesystem | blob
    STORAGE_TYPE: str = "filesystem"
    BLOB_STORAGE_ACCOUNT_NAME: str | None = None
    AGENT_PACKAGE_CONTAINER: str = "agent-packages"
    AZURE_STORAGE_CONNECTION_STRING: str | None = None

    # CORS Settings
    BACKEND_CORS_ORIGINS: list[str] = [
        "https://portal.azure.com",
        "https://ms.portal.azure.com",
        "https://localhost:53000",
        "http://localhost:53000",
        "http://localhost:3000",
        "https://localhost:3000",
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
