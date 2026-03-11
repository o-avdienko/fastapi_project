from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/url_shortener"
    REDIS_URL: str = "redis://redis:6379"
    SECRET_KEY: str = "secretkey_12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    UNUSED_LINK_DAYS: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
