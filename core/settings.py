from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    DB_URL: str
    JWT_ALGORITHM: str
    JWT_ACCESS_EXPIRY: int
    JWT_REFRESH_EXPIRY: int
    SECRET_KEY: str


settings = Settings()
