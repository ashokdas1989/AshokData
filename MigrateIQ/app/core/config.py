from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://migrateiq:migrateiq@localhost:5432/migrateiq"
    OPENAI_API_KEY: str = ""
    SECRET_KEY: str = "change-me"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    APP_NAME: str = "MigrateIQ"
    VERSION: str = "1.0.0"

    class Config:
        env_file = ".env"


settings = Settings()
