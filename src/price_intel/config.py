from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Ecommerce Price Intel"
    api_port: int = 8100
    db_url: str = "sqlite:///./data/catalog.db"


settings = Settings()


def database_path(db_url: str | None = None) -> Path:
    url = make_url(db_url or settings.db_url)
    if url.get_backend_name() != "sqlite" or not url.database or url.database == ":memory:":
        raise ValueError("DB_URL must point to a file-backed SQLite database")
    return Path(url.database)
