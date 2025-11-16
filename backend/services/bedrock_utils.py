from __future__ import annotations

import json
import re
from typing import Any

from botocore.exceptions import BotoCoreError, ClientError

from config import get_settings
from utils.auth_aws import get_session

CLASSIFICATION_LABELS = ["議事進行", "報告", "提案", "相談", "質問", "回答", "決定", "無関係な雑談"]


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


def classify_transcript_segments(segments: list[dict[str, Any]], client: Any | None = None) -> list[dict[str, Any]]:
    clean_segments = []
    for segment in segments:
        text = (segment.get("text") or "").strip()
        if not text:
            continue
        clean_segments.append(
            {
                "index": segment.get("index"),
                "speaker": segment.get("speaker") or "",
                "text": text,
                "context_before": (segment.get("context_before") or "").strip(),
                "context_after": (segment.get("context_after") or "").strip(),
            }
        )
    if not clean_segments:
        return []

    settings = get_settings()
    prompt = (
        "あなたは日本語の議事録を文単位で分類するアシスタントです。\n"
        "各文を次のカテゴリのうち1つに必ず割り当ててください:\n"
        f"{', '.join(CLASSIFICATION_LABELS)}。\n"
        "context_before と context_after で前後の文脈を参考にしながら、文脈に沿った分類を行ってください。\n"
        "レスポンスは JSON 配列で、各要素は {\"index\":番号,\"category\":\"分類名\"} の形にしてください。\n"
        "以下の文一覧を分類してください:\n"
        f"{json.dumps(clean_segments, ensure_ascii=False)}"
    )
    payload = {
        "prompt": prompt,
        "maxTokens": 512,
        "temperature": 0.2,
    }
    try:
        response = _bedrock_client(client).invoke_model(
            modelId=settings.bedrock_model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload).encode("utf-8"),
        )
        content = _load_json_body(response)
        parsed = _coerce_classifications(content)
        if parsed:
            return _merge_classifications(clean_segments, parsed)
    except (BotoCoreError, ClientError):
        pass

    return []


def _coerce_classifications(content: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = content.get("classifications")
    if isinstance(candidates, list):
        return candidates
    for key in ("outputText", "completion", "response"):
        raw = content.get(key)
        if not raw:
            continue
        if isinstance(raw, str):
            raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict) and isinstance(parsed.get("classifications"), list):
                return parsed["classifications"]
        except json.JSONDecodeError:
            matches = re.findall(r'\{[^}]*"category"\s*:\s*"[^"]+"[^}]*\}', raw)
            if matches:
                try:
                    return [json.loads(match) for match in matches]
                except json.JSONDecodeError:
                    continue
    return []


def _merge_classifications(segments: list[dict[str, Any]], classified: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index_to_category = {}
    for item in classified:
        idx = item.get("index")
        cat = item.get("category")
        if isinstance(idx, int) and isinstance(cat, str):
            index_to_category[idx] = cat

    merged: list[dict[str, Any]] = []
    for segment in segments:
        idx = segment["index"]
        category = index_to_category.get(idx, _guess_category(segment["text"]))
        if category not in CLASSIFICATION_LABELS:
            category = "無関係な雑談"
        merged.append({**segment, "category": category})
    return merged


def _fallback_classification(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {**segment, "category": _guess_category(segment["text"])}
        for segment in segments
    ]


def _guess_category(text: str) -> str:
    lowered = text.lower()
    cues = [
        ("議事進行", ["議題", "進行", "次に", "本題", "開始", "終了"]),
        ("報告", ["報告", "共有", "アップデート", "結果", "進捗", "ステータス"]),
        ("提案", ["提案", "アイデア", "案", "どうでしょう", "検討"]),
        ("相談", ["相談", "一緒に", "助け", "サポート", "悩んで"]),
        ("質問", ["?", "か?", "教えて", "でしょうか", "質問"]),
        ("回答", ["回答", "説明します", "対応します", "お答え", "承知"]),
        ("決定", ["決定", "合意", "確定", "承認", "決めましょう"]),
        ("無関係な雑談", ["雑談", "世間話", "余談", "週末", "天気", "ランチ"]),
    ]
    for label, keywords in cues:
        if any(keyword in text for keyword in keywords) or any(keyword in lowered for keyword in keywords):
            return label
    return "無関係な雑談"
