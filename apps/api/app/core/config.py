from pydantic_settings import BaseSettings
from functools import lru_cache
from pathlib import Path

# Resolve .env relative to THIS file, not the cwd — works from any launch directory
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str = "changeme-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    APP_NAME: str = "OVERSIGHT"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # OTP
    OTP_EXPIRE_MINUTES: int = 5
    DEMO_MODE: bool = True  # Returns OTP in response for demo/testing

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    # LiveKit
    LIVEKIT_URL: str = "ws://localhost:7880"
    LIVEKIT_API_KEY: str = "devkey"
    LIVEKIT_API_SECRET: str = "devsecret"

    class Config:
        env_file = str(ENV_FILE)
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
