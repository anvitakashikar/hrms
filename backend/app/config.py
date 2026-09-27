from functools import lru_cache
from typing import Any

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "HRMS Core"
    database_url: str = "mongodb://localhost:27017"
    database_name: str = "hrms_core_db"
    jwt_secret_key: str = "super-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


class AppConfig(BaseModel):
    settings: Any = None
