from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    DB_URL: str
    JWT_ALGORITHM: str


settings = Settings()
