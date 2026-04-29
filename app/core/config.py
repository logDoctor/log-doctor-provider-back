import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# ENV 또는 TEAMSFX_ENV 환경 변수에 따라 .env.dev 또는 .env.prod를 로드합니다.
# 기본값은 dev입니다.
env = os.getenv("ENV") or os.getenv("TEAMSFX_ENV") or "dev"
env_file = f".env.{env}"

print(f">>> Loading environment settings from: {env_file}")


class Settings(BaseSettings):
    # Authentication Settings
    # AUTH_METHOD: managed_identity | secret | mock
    AUTH_METHOD: str = "managed_identity"

    # Azure AD Settings
    # Managed Identity 사용 시 필요하지 않을 수 있으나, AUTH_METHOD="secret"인 경우 .env에서 주입받습니다.
    CLIENT_ID: str | None = None
    CLIENT_SECRET: str | None = None
    TENANT_ID: str | None = None
    TAB_RESOURCE_DOMAIN: str | None = None
    TEAMS_APP_ID: str

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

    # App Role IDs
    TENANT_ADMIN_ROLE_ID: str | None = None
    PRIVILEGED_USER_ROLE_ID: str | None = None
    PLATFORM_ADMIN_ROLE_ID: str | None = None

    # Support Settings
    SUPPORT_CHANNEL_ID: str | None = None
    SUPPORT_SERVICE_URL: str = "https://smba.trafficmanager.net/kr/"

    # Agent Discovery Settings
    AGENT_TAG_NAME: str = "log-doctor-role"
    AGENT_TAG_VALUE: str = "agent-storage"

    # Storage Settings
    # STORAGE_TYPE: filesystem | blob
    STORAGE_TYPE: str = "filesystem"
    BLOB_STORAGE_ACCOUNT_NAME: str | None = None
    AGENT_PACKAGE_CONTAINER: str = "agent-packages"
    AZURE_STORAGE_CONNECTION_STRING: str | None = None

    # CORS Settings
    # 기본 허용 주소 (Azure Portal, Teams 등)
    COMMON_CORS_ORIGINS: list[str] = [
        "https://portal.azure.com",
        "https://ms.portal.azure.com",
        "https://teams.microsoft.com",
    ]
    # .env에서 로드된 환경별 추가 주소
    BACKEND_CORS_ORIGINS: str | list[str] = ""

    @property
    def cors_origins(self) -> list[str]:
        """기본 주소와 환경별 주소를 병합하여 최종 허용 목록을 반환합니다."""
        origins = list(self.COMMON_CORS_ORIGINS)

        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            if self.BACKEND_CORS_ORIGINS:
                # 쉼표로 구분된 문자열을 리스트로 변환
                extra_origins = [
                    o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()
                ]
                origins.extend(extra_origins)
        elif isinstance(self.BACKEND_CORS_ORIGINS, list):
            origins.extend(self.BACKEND_CORS_ORIGINS)

        return list(set(origins))  # 중복 제거

    model_config = SettingsConfigDict(env_file=env_file, extra="ignore")


settings = Settings()
