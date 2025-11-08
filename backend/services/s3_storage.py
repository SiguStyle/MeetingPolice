from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from config import get_settings
from utils.auth_aws import get_session


class S3Storage:
    """Wrapper that prefers S3 but falls back to local disk for dev."""

    def __init__(self, bucket: str | None = None, client: Any | None = None):
        self.settings = get_settings()
        self.bucket = bucket or self.settings.s3_bucket_name
        session = get_session()
        self.client = client or session.client("s3")
        self._fallback_dir = Path(__file__).resolve().parents[1] / "data" / "s3"
        self._fallback_dir.mkdir(parents=True, exist_ok=True)

    def list_objects(self, prefix: str = "") -> list[str]:
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            keys: list[str] = []
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                keys.extend(obj["Key"] for obj in page.get("Contents", []))
            return keys
        except (BotoCoreError, ClientError):
            base = self._fallback_dir / prefix
            if not base.exists():
                return []
            return [str(path.relative_to(self._fallback_dir)) for path in base.rglob("*") if path.is_file()]

    def read_text(self, key: str) -> str:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read().decode("utf-8")
        except (BotoCoreError, ClientError):
            path = self._fallback_dir / key
            if not path.exists():
                raise FileNotFoundError(key)
            return path.read_text(encoding="utf-8")

    def write_json(self, key: str, data: dict) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=payload, ContentType="application/json")
        except (BotoCoreError, ClientError):
            path = self._fallback_dir / key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
