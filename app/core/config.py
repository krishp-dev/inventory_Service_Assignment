import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Set

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:inventory@localhost:5432/inventory"
    )
    TEST_DATABASE_URL: str = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+psycopg2://postgres:inventory@localhost:5432/inventory_test"
    )
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "inventory-service-secret-key-32-chars-long"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    MANAGED_ATTRIBUTES: Set[str] = {"color", "size", "weight_grams"}

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

