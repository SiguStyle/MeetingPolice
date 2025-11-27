from __future__ import annotations

import asyncio
from typing import Iterable, Iterator, Any

from botocore.exceptions import BotoCoreError, ClientError

from backend.utils.auth_aws import get_session
from backend.config import get_settings


class _AudioStream:
    def __init__(self, chunks: Iterable[bytes]):
        self._chunks = chunks

    def __iter__(self) -> Iterator[dict[str, Any]]:
        for chunk in self._chunks:
            yield {"AudioEvent": {"AudioChunk": chunk}}


class TranscribeStream:
    def __init__(self, client: Any | None = None):
        session = get_session()
        # `transcribe-streaming` is not a standalone boto3 service; streaming APIs live under the `transcribe` client.
        self.client = client or session.client("transcribe", region_name=get_settings().aws_region)

    async def start(self, audio_stream: Iterable[bytes] | None = None) -> str:
        chunks = audio_stream or self._silence_chunks()
        try:
            response = await asyncio.to_thread(
                self.client.start_stream_transcription,
                LanguageCode="ja-JP",
                MediaEncoding="pcm",
                MediaSampleRateHertz=16000,
                AudioStream=_AudioStream(chunks),
            )
            return response.get("SessionId", "transcribe_session_started")
        except (BotoCoreError, ClientError) as exc:
            return f"error: {exc}"

    def _silence_chunks(self, seconds: int = 2, chunk_size: int = 3200) -> Iterator[bytes]:
        total_chunks = max(1, (seconds * 16000) // chunk_size)
        silence = b"\x00" * chunk_size
        for _ in range(total_chunks):
            yield silence
