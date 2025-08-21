from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    github_org: str
    github_token: str
    model_config = SettingsConfigDict(env_file=".env")