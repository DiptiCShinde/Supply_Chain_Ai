from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "dev"
    database_url: str = ""
    redis_url: str = ""
    api_key: str = "dev-key"
    llm_api_key: str = ""
    mock_llm: bool = True

    model_config = SettingsConfigDict(env_file=".env.dev", extra="ignore")


settings = Settings()