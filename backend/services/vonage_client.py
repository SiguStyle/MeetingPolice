from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import jwt

from config import get_settings


class VonageClient:
    def __init__(self):
        self.settings = get_settings()
        key_path = Path(self.settings.vonage_private_key_path)
        self.private_key = key_path.read_text() if key_path.exists() else None

    def create_session(self, meeting_id: str) -> dict[str, Any]:
        # 実際には Vonage Video REST API を呼び出す想定
        return {"session_id": f"session-{meeting_id}"}

    def generate_token(self, session_id: str, ttl_seconds: int = 300) -> str:
        payload = {
            "iss": self.settings.vonage_application_id,
            "sub": self.settings.vonage_application_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + ttl_seconds,
            "acl": {"paths": {"/*": {}}},
            "session_id": session_id,
        }
        if not self.private_key:
            return f"mock-token-{session_id}"
        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        return token
