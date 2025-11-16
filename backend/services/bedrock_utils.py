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


def _model_uses_messages(model_id: str) -> bool:
    return "claude-3" in (model_id or "").lower()


def _invoke_text_model(prompt: str, max_tokens: int, temperature: float, client: Any | None = None) -> dict[str, Any]:
    settings = get_settings()
    model_id = settings.bedrock_model_id
    if _model_uses_messages(model_id):
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt,
                        }
                    ],
                }
            ],
        }
    else:
        payload = {
            "prompt": prompt,
            "maxTokens": max_tokens,
            "temperature": temperature,
        }

    response = _bedrock_client(client).invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload).encode("utf-8"),
    )
    return _load_json_body(response)


def _extract_text_from_content(content: dict[str, Any]) -> str:
    for key in ("outputText", "completion", "response"):
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    message_content = content.get("content")
    if isinstance(message_content, list):
        pieces: list[str] = []
        for item in message_content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text.strip():
                pieces.append(text.strip())
        if pieces:
            return "\n".join(pieces)
    return ""


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
    prompt = f"以下は会議ID {meeting_id} の議事録です。日本語で簡潔に要約してください。\n{transcript_text[:4000]}"
    try:
        content = _invoke_text_model(prompt, max_tokens=256, temperature=0.3, client=client)
        summary_text = _extract_text_from_content(content) or json.dumps(content)
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

    category_guidance = (
        "議事進行=会議の段取りや進め方/次の議題の指示、開始・終了宣言、アジェンダの提示\n"
        "報告=進捗や結果、現状共有。担当や出欠の自己紹介（「ヤマモトです」「開発の田中です」など）も含む\n"
        "提案=新しい案や改善点の持ちかけ。「〜してはどうでしょうか」「〜しませんか」など\n"
        "相談=協力依頼や迷いの吐露。「どうしたらいいか迷っています」「相談させてください」など\n"
        "質問=情報を求める発言。「〜ですか？」「〜でしょうか」「教えてください」など\n"
        "回答=質問への答え・説明、または依頼への承諾/却下。「はい、〜します」「大丈夫です」など\n"
        "決定=意思決定や合意事項の明言。「〜で決定します」「この方針で行きましょう」など\n"
        "コメント=議題や業務内容に関する感想・評価・共感・軽い相づち。新しい情報や決定を含まない短い発言\n"
        "無関係な雑談=業務や会議の議題と直接関係しない雑談（天気・プライベート・関係ない雑感など）。\n"
        "                 会議の開始時挨拶や自己紹介、了解の返事などはここに含めない"
    )

    prompt = (
        "あなたは日本語の議事録を文単位で分類するアシスタントです。\n"
        "必ず同じ基準で安定した判断を行い、文脈(context_before/context_after)も考慮してください。\n"
        "\n"
        "カテゴリ定義:\n"
        f"{category_guidance}\n"
        "\n"
        "判定ルール:\n"
        "1. 名乗り・自己紹介（例:「サトウです」「高橋です」）は、会議参加や担当を示す発言として「報告」とする。\n"
        "   特に、文全体が「固有名詞 + です。」の形になっている場合は「報告」を優先する。\n"
        "2. 「はい」「了解しました」「大丈夫です」「お願いします」など、固有名詞を含まない短い返事は、\n"
        "   直前の質問や依頼に対する「回答」として扱う。\n"
        "3. アジェンダや議題の提示（例:「今日のアジェンダは〜です」「次の議題は〜です」）は「議事進行」とする。\n"
        "4. 進捗や状況に関する評価（例:「想定よりも順調に進んでいます」「少し遅れています」）は「報告」とする。\n"
        "5. 会議内容に対する感想・共感・軽い相づち（例:「それは心強いですね」「助かります」「よかったです」）は\n"
        "   新しい情報や方針・決定を含まない限り「コメント」として分類する。\n"
        "6. 文末が「〜でしょうか」「〜ですか」「〜ませんか」「〜かね」など「か」で終わる文は、\n"
        "   内容に説明や提案が含まれていても、必ず「質問」として分類する。\n"
        "7. 「〜したいと考えています」「〜してはどうでしょうか」「〜できればと思います」など、\n"
        "   新しい行動・方針を持ちかけている文は「提案」とする。\n"
        "8. 直前の質問「〜でよいですか？」「〜で大丈夫でしょうか？」に対して、\n"
        "   「はい、そのつもりで準備しています」「はい、大丈夫です」などと答える文は「回答」とする。\n"
        "9. 「〜で行きましょう」「〜でリリースします」など、方針やスケジュールを確定する発言は「決定」とする。\n"
        "10. 「コメント」と「無関係な雑談」の違い:\n"
        "    - 議題や業務内容に対する感想・評価・共感 → 「コメント」\n"
        "    - 天気・私生活・趣味など議題と無関係な話題 → 「無関係な雑談」\n"
        "11. どのカテゴリにも当てはまらないからといって安易に「無関係な雑談」を選ばない。\n"
        "    明らかに業務や議題と無関係な話題のみを「無関係な雑談」とする。\n"
        "\n"
        "【分類例】（これは出力ではなく、ルール理解のための例です）\n"
        "・「サトウです。」 → 報告\n"
        "・「今日のアジェンダは新機能の進捗と来月のイベント対応です。」 → 議事進行\n"
        "・「それは心強いですね。」 → コメント\n"
        "・「来週水曜日のリリースは、予定どおり進めて大丈夫そうでしょうか。」 → 質問\n"
        "・「はい、そのつもりで準備しています。」 → 回答\n"
        "・「ただ、月曜日の午後にもう一度だけ付加試験を実施したいと考えています。」 → 提案\n"
        "\n"
        "出力形式は JSON 配列のみで、各要素は {\"index\":番号,\"category\":\"分類名\"} です。\n"
        "未知のカテゴリは使わず、必ず上記ラベルのいずれか1つを割り当ててください。\n"
        "最後の出力には JSON 以外の文字は一切含めないでください。\n"
        "\n"
        "以下の文一覧を分類してください:\n"
        f"{json.dumps(clean_segments, ensure_ascii=False)}"
    )

    try:
        content = _invoke_text_model(prompt, max_tokens=512, temperature=0.2, client=client)
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
    raw = _extract_text_from_content(content)
    if raw:
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
                    pass
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
