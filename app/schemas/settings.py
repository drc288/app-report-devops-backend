from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    github_org: str
    github_token: str
    mongo_string_connection: str
    mongo_collection_name: str
    backstage_token: str
    cors_origins: str
    sonarcloud_token: str
    sonarcloud_org: str
    model_config = SettingsConfigDict(env_file=".env")