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

    # GitHub App Configuration
    github_app_id: str
    github_app_client_id: str
    github_app_private_key_path: str = "devops.pem"
    github_app_installation_id: str = ""  # Optional, will be auto-detected if empty
    use_github_app: bool = True  # Flag to enable/disable GitHub App auth

    model_config = SettingsConfigDict(env_file=".env")