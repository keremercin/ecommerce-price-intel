from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Ecommerce Price Intel"
    api_port: int = 8100
    db_url: str = "sqlite:///./price_intel.db"


settings = Settings()
