from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    SECRET_KEY: str = "change_me"
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@postgres:5432/laboratorio"
    OPENAI_API_KEY: str = ""
    BASE_URL: str = "http://localhost:8000"
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]


settings = Settings()
