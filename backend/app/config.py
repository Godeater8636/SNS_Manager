from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application
    APP_NAME: str = "SNS Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://sns_user:sns_pass@localhost:5432/sns_manager"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_PRIVATE_KEY: str = ""
    JWT_PUBLIC_KEY: str = ""
    JWT_ALGORITHM: str = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Encryption (AES-256-GCM)
    AES_ENCRYPTION_KEY: str = ""  # 32 bytes, base64 encoded
    AES_KEY_ID: str = "v1"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_S3_BUCKET: str = "sns-manager-media"
    AWS_REGION: str = "ap-northeast-1"

    # Email
    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@sns-mgr.app"

    # App base URL (for short links)
    APP_BASE_URL: str = "http://localhost:8000"

    # Local file storage (used when AWS_ACCESS_KEY_ID is not set)
    LOCAL_STORAGE_PATH: str = "./media"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"


settings = Settings()
