from __future__ import annotations

import json
import re
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
    prompt = f"以下は会議ID {meeting_id} の議事録です。日本語で簡潔に要約してください。\n{transcript_text[:4000]}"
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


def extract_keywords(text: str, max_keywords: int = 5, client: Any | None = None) -> list[str]:
    """
    Ask Bedrock to return top keywords for a single utterance.
    Falls back to a simple heuristic split when Bedrock is unavailable.
    """
    settings = get_settings()
    clipped = text.strip()
    if not clipped:
        return []

    prompt = (
        "あなたは日本語のキーワード抽出アシスタントです。\n"
        "以下の発話から重要なキーワードを最大"
        f"{max_keywords}件まで抽出し、JSON 形式 {{\"keywords\": [\"キーワード1\", ...]}} で返してください。\n"
        f"発話: {clipped[:600]}"
    )
    payload = {
        "prompt": prompt,
        "maxTokens": 128,
        "temperature": 0.1,
    }

    try:
        response = _bedrock_client(client).invoke_model(
            modelId=settings.bedrock_model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8"),
        )
        content = _load_json_body(response)
        keywords = _coerce_keywords(content)
        if keywords:
            return keywords[:max_keywords]
    except (BotoCoreError, ClientError):
        pass

    return _fallback_keywords(clipped, max_keywords)


def _coerce_keywords(content: dict[str, Any]) -> list[str]:
    keywords = content.get("keywords")
    if isinstance(keywords, list):
        return [str(item) for item in keywords if str(item).strip()]
    for key in ("outputText", "completion", "response"):
        blob = content.get(key)
        if not isinstance(blob, str):
            continue
        blob = blob.strip()
        if not blob:
            continue
        try:
            parsed = json.loads(blob)
            if isinstance(parsed, dict) and isinstance(parsed.get("keywords"), list):
                return [str(item) for item in parsed["keywords"] if str(item).strip()]
        except json.JSONDecodeError:
            matches = re.findall(r"[\"“”']([^\"“”']+)[\"“”']", blob)
            if matches:
                return [item.strip() for item in matches if item.strip()]
            parts = [part.strip(" ・,;") for part in blob.splitlines() if part.strip()]
            if parts:
                return parts
    return []


def _fallback_keywords(text: str, max_keywords: int) -> list[str]:
    tokens = [tok for tok in re.split(r"[^\wぁ-んァ-ヶ一-龠ー]+", text) if len(tok) > 1]
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)
        if len(keywords) >= max_keywords:
            break
    return keywords
