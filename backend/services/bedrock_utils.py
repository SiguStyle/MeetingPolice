from __future__ import annotations

import json
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from config import get_settings
from utils.auth_aws import get_session


def _bedrock_client(client: Any | None = None):
    if client:
        return client
    session = get_session()
    return session.client("bedrock-runtime", region_name=get_settings().aws_region)


def _load_json_body(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body")
    if hasattr(body, "read"):
        raw = body.read()
    elif isinstance(body, (bytes, bytearray)):
        raw = body
    elif body is None:
        return {}
    else:
        raw = str(body).encode("utf-8")
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {"outputText": raw.decode("utf-8")}


def create_embedding(text: str, client: Any | None = None) -> list[float]:
    settings = get_settings()
    payload = {"inputText": text}
    try:
        response = _bedrock_client(client).invoke_model(
            modelId=settings.bedrock_model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8"),
        )
        content = _load_json_body(response)
        embedding = content.get("embedding") or content.get("embeddings")
        if isinstance(embedding, list):
            # flatten nested arrays if needed
            return embedding[0] if embedding and isinstance(embedding[0], list) else embedding
        return [0.0]
    except (BotoCoreError, ClientError):
        return [hash(text) % 100 / 100 for _ in range(16)]


def summarize_transcript(meeting_id: str, transcript_text: str, client: Any | None = None) -> dict[str, Any]:
    settings = get_settings()
    prompt = f"Summarize meeting {meeting_id}:\n{transcript_text[:4000]}"
    payload = {
        "prompt": prompt,
        "maxTokens": 256,
        "temperature": 0.3,
    }
    try:
        response = _bedrock_client(client).invoke_model(
            modelId=settings.bedrock_model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8"),
        )
        content = _load_json_body(response)
        summary_text = (
            content.get("outputText")
            or content.get("completion")
            or content.get("response")
            or json.dumps(content)
        )
    except (BotoCoreError, ClientError):
        summary_text = f"[mock-summary] {prompt[:200]}"

    return {"meeting_id": meeting_id, "summary": summary_text}
