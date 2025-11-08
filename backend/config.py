from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import BaseSettings, AnyHttpUrl


class Settings(BaseSettings):
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    cors_origins: List[AnyHttpUrl] | List[str] = ["http://localhost:5173", "http://localhost:5174"]

    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    s3_bucket_name: str = "meeting-police-dev"
    bedrock_model_id: str = "anthropic.claude-v2"
    comprehend_language: str = "en"

    vonage_application_id: str = ""
    vonage_api_key: str = ""
    vonage_api_secret: str = ""
    vonage_private_key_path: str = "secrets/vonage_private.key"

    class Config:
        env_file = str(Path(__file__).resolve().parents[1] / ".env")
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
