from functools import lru_cache
from pathlib import Path
from typing import Any, List

from pydantic import AnyHttpUrl, PostgresDsn, field_validator

try:  # pragma: no cover - runtime fallback for pydantic>=2.0
    from pydantic import BaseSettings  # type: ignore
except ImportError:  # pragma: no cover
    from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    app_name: str = "TaskMate AI Backend"
    environment: str = "development"
    debug: bool = False

    database_dsn: PostgresDsn = "postgresql+psycopg://postgres:postgres@db:5432/taskmate"
    redis_url: str = "redis://redis:6379/0"

    app_base_url: AnyHttpUrl | None = None

    openai_api_key: str | None = None
    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None
    telegram_webhook_secret_token: str | None = None
    zibal_merchant_id: str | None = None
    cryptobot_api_token: str | None = None

    jwt_secret: str = "change-me"
    jwt_admin_expires_hours: int = 24
    jwt_orgadmin_expires_hours: int = 24

    default_timezone: str = "Europe/Stockholm"
    default_locale: str = "en"
    file_retention_days: int = 7
    files_storage_dir: Path = Path("/var/taskmate/uploads")
    files_signing_secret: str | None = None

    sentry_dsn: AnyHttpUrl | None = None
    log_level: str = "INFO"

    enable_eigan_sync: bool = False
    enable_clickup_sync: bool = False

    cors_allow_origins: List[AnyHttpUrl] = []

    class Config:
        env_file = Path(__file__).resolve().parents[2] / ".env"
        case_sensitive = False

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def split_origins(cls, value: Any) -> List[AnyHttpUrl]:
        if not value:
            return []
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()  # type: ignore[arg-type]


settings = get_settings()
