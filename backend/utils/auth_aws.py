import boto3
from functools import lru_cache

from config import get_settings


@lru_cache
def get_session():
    settings = get_settings()
    session_kwargs = {
        "region_name": settings.aws_region,
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        session_kwargs.update(
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
        )

    return boto3.Session(**session_kwargs)
