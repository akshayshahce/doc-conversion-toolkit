from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Doc Conversion Toolkit"
    api_prefix: str = "/api"
    max_upload_mb: int = 200
    temp_prefix: str = "doc_toolkit_"
    frontend_dist: Path = Field(default=Path(__file__).resolve().parents[3] / "frontend" / "dist")

    model_config = SettingsConfigDict(env_prefix="DOC_TOOLKIT_", env_file=".env", extra="ignore")


settings = Settings()
