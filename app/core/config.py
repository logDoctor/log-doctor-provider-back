from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Authentication Settings
    # AUTH_METHOD: managed_identity | secret | mock
    AUTH_METHOD: str = "secret"

    # Azure AD Settings
    # Managed Identity 사용 시 필요하지 않을 수 있으나, AUTH_METHOD="secret"인 경우 .env에서 주입받습니다.
    CLIENT_ID: str | None = None
    CLIENT_SECRET: str | None = None
    TENANT_ID: str | None = None
    APP_ID_URI: str | None = (
        None  # Teams SSO Token의 Audience 검증용 (예: api://localhost:53000/{CLIENT_ID})
    )

    # Cosmos DB Settings
    COSMOS_ENDPOINT: str = "https://mock-cosmos.documents.azure.com:443/"
    COSMOS_DATABASE: str = "log-doctor-db"
    COSMOS_KEY: str | None = None
    AZURE_COSMOS_DISABLE_SSL: bool = False

    # CORS Settings
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
