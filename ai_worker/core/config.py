import zoneinfo
from dataclasses import field

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))

    REDIS_URL: str = "redis://localhost:6379"
    OPENAI_API_KEY: str = ""

    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "ai_health"
    DB_PASSWORD: str = "ai_health_pw"
    DB_NAME: str = "ai_health_db"

    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"

    CLOVA_OCR_INVOKE_URL: str = ""
    CLOVA_OCR_SECRET_KEY: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


config = Config()
