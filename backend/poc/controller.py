from __future__ import annotations

import asyncio
import audioop
import io
import json
import uuid
import wave
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from amazon_transcribe.auth import StaticCredentialResolver
from amazon_transcribe.client import TranscribeStreamingClient

from config import get_settings
from services.bedrock_utils import summarize_transcript
from services.comprehend_utils import analyze_sentiment
from utils.auth_aws import get_session
from utils.time_utils import now_iso


@dataclass
class PocJob:
    job_id: str
    agenda_text: str
    audio_filename: str
    created_at: str = field(default_factory=now_iso)
    status: str = "processing"
    transcripts: list[dict[str, Any]] = field(default_factory=list)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    speaker_labels: dict[str, str] = field(default_factory=dict)
    next_speaker_index: int = 1
    next_entry_index: int = 1
    pending_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    processed_result_ids: set[str] = field(default_factory=set)


class POCController:
    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or Path(__file__).resolve().parents[1] / "data" / "poc"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, PocJob] = {}
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)

    async def start_transcription(self, agenda_text: str, audio_filename: str, audio_bytes: bytes) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = PocJob(job_id=job_id, agenda_text=agenda_text, audio_filename=audio_filename)
        self.jobs[job_id] = job

        job_dir = self._job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "agenda.txt").write_text(agenda_text, encoding="utf-8")
        (job_dir / "audio.bin").write_bytes(audio_bytes)

        asyncio.create_task(self._process_audio(job, audio_bytes))
        return job_id

    def get_job(self, job_id: str) -> PocJob | None:
        return self.jobs.get(job_id)

    def get_job_payload(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        return {
            "job_id": job.job_id,
            "status": job.status,
            "agenda_text": job.agenda_text,
            "audio_filename": job.audio_filename,
            "created_at": job.created_at,
            "transcripts": job.transcripts,
        }

    async def analyze_job(self, job_id: str) -> dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            raise KeyError(job_id)
        if not job.transcripts:
            raise ValueError("Transcription not ready yet")

        transcript_text = "\n".join(f"{item['speaker']}: {item['text']}" for item in job.transcripts)
        summary = summarize_transcript(job_id, transcript_text)
        sentiment = analyze_sentiment(transcript_text[:4000])

        guidance = [
            "Use the summarized transcript as input for Bedrock to draft meeting minutes or action items.",
            "Send the combined agenda text and transcript text to Comprehend for sentiment or entity detection.",
            "Persist agenda + transcript pairs so Bedrock can learn how discussions follow agenda items.",
        ]

        return {
            "job_id": job.job_id,
            "agenda_text": job.agenda_text,
            "summary": summary,
            "sentiment": sentiment,
            "transcript_sample": job.transcripts[:5],
            "guidance": guidance,
        }

    async def _process_audio(self, job: PocJob, audio_bytes: bytes) -> None:
        try:
            pcm_bytes, sample_rate = self._prepare_pcm(audio_bytes)
            await self._run_transcribe_stream(job, pcm_bytes, sample_rate)
        except Exception:
            self.logger.exception("Transcribe streaming failed for job %s, fallback to mock data", job.job_id)
            job.transcripts.clear()
            await self._simulate_stream(job)

    async def _simulate_stream(self, job: PocJob) -> None:
        script = self._build_script(job)
        job_dir = self._job_dir(job.job_id)
        transcript_path = job_dir / "transcripts.json"
        for idx, line in enumerate(script, start=1):
            payload = {
                "index": idx,
                "speaker": "Speaker A" if idx % 2 else "Speaker B",
                "raw_speaker": "spk_mock_a" if idx % 2 else "spk_mock_b",
                "result_id": f"mock-{idx}",
                "text": line,
                "timestamp": now_iso(),
            }
            job.transcripts.append(payload)
            job.next_entry_index = max(job.next_entry_index, idx + 1)
            await job.queue.put({"type": "transcript", "action": "append", "payload": payload})
            await asyncio.sleep(1.2)
        job.status = "completed"
        transcript_path.write_text(json.dumps(job.transcripts, ensure_ascii=False, indent=2), encoding="utf-8")
        await job.queue.put({"type": "complete"})

    def _build_script(self, job: PocJob) -> list[str]:
        agenda_lines = [
            line.strip(" -*•\t")
            for line in job.agenda_text.splitlines()
            if line.strip(" -*•\t")
        ]
        script: list[str] = []
        if agenda_lines:
            for line in agenda_lines:
                script.append(f"Agenda topic: {line}")
                script.append(f"Discussion: Confirming action items for '{line}'.")

        if not script:
            script.append(f"Processing uploaded audio file '{job.audio_filename}'")

        fallback_segments = max(3, min(10, len(job.audio_filename) // 2))
        for idx in range(fallback_segments):
            script.append(f"Speaker {chr(65 + idx % 2)} shares update part {idx + 1}.")

        return script[:12]

    def _job_dir(self, job_id: str) -> Path:
        return self.storage_dir / job_id

    def _prepare_pcm(self, audio_bytes: bytes) -> tuple[bytes, int]:
        try:
            with wave.open(io.BytesIO(audio_bytes), "rb") as wav:
                sample_width = wav.getsampwidth()
                sample_rate = wav.getframerate()
                channels = wav.getnchannels()
                raw = wav.readframes(wav.getnframes())
        except wave.Error:
            # assume already PCM (e.g. raw upload)
            return audio_bytes, 16000

        target_width = 2
        if sample_width != target_width:
            raw = audioop.lin2lin(raw, sample_width, target_width)
            sample_width = target_width

        if channels != 1:
            raw = audioop.tomono(raw, sample_width, 0.5, 0.5)
            channels = 1

        target_rate = 16000
        if sample_rate != target_rate:
            raw, _ = audioop.ratecv(raw, sample_width, channels, sample_rate, target_rate, None)
            sample_rate = target_rate

        return raw, sample_rate

    async def _run_transcribe_stream(self, job: PocJob, pcm_bytes: bytes, sample_rate: int) -> None:
        session = get_session()
        credentials = session.get_credentials()
        if not credentials:
            raise RuntimeError("Unable to resolve AWS credentials for Transcribe streaming")
        frozen = credentials.get_frozen_credentials()
        credential_resolver = StaticCredentialResolver(
            frozen.access_key,
            frozen.secret_key,
            frozen.token,
        )
        client = TranscribeStreamingClient(
            region=self.settings.aws_region,
            credential_resolver=credential_resolver,
        )
        chunk_ms = 50
        chunk_bytes = max(1, int(sample_rate * 2 * chunk_ms / 1000))

        self.logger.info(
            "Starting Transcribe stream job_id=%s sample_rate=%s chunk_bytes=%s",
            job.job_id,
            sample_rate,
            chunk_bytes,
        )
        stream = await client.start_stream_transcription(
            language_code="ja-JP",
            media_encoding="pcm",
            media_sample_rate_hz=sample_rate,
            show_speaker_label=True,
            enable_partial_results_stabilization=True,
            partial_results_stability="medium",
        )

        async def send_audio():
            chunk_delay = chunk_ms / 1000
            for chunk in self._chunk_pcm(pcm_bytes, chunk_bytes):
                await stream.input_stream.send_audio_event(audio_chunk=chunk)
                await asyncio.sleep(chunk_delay)
            await stream.input_stream.end_stream()

        async def consume_results():
            async for event in stream.output_stream:
                transcript = getattr(event, "transcript", None)
                if not transcript:
                    continue
                for result in getattr(transcript, "results", []) or []:
                    result_id = getattr(result, "result_id", None)
                    if not result_id:
                        continue
                    is_partial = getattr(result, "is_partial", False)
                    if not is_partial and result_id in job.processed_result_ids:
                        continue
                    alternatives = getattr(result, "alternatives", []) or []
                    if not alternatives:
                        continue
                    alternative = alternatives[0]
                    text = (getattr(alternative, "transcript", "") or "").strip()
                    if not text:
                        continue
                    speaker_label, raw_label = self._speaker_from_items(job, alternative)
                    await self._handle_result(job, result_id, speaker_label, raw_label, text, not is_partial)
                    if not is_partial:
                        job.processed_result_ids.add(result_id)

        success = False
        try:
            await asyncio.gather(send_audio(), consume_results())
            success = True
        finally:
            await self._finalize_pending_results(job)
            if success:
                job.status = "completed"
                await job.queue.put({"type": "complete"})
                self.logger.info("Transcribe stream completed job_id=%s total_segments=%s", job.job_id, len(job.transcripts))

    def _chunk_pcm(self, pcm_bytes: bytes, chunk_size: int):
        for idx in range(0, len(pcm_bytes), chunk_size):
            yield pcm_bytes[idx : idx + chunk_size]

    def _speaker_name(self, job: PocJob, raw_label: str | None) -> str:
        key = raw_label or "__unknown__"
        if key not in job.speaker_labels:
            label = f"Speaker {job.next_speaker_index}"
            job.speaker_labels[key] = label
            job.next_speaker_index += 1
        return job.speaker_labels[key]

    def _speaker_from_items(self, job: PocJob, alternative: Any) -> tuple[str, str]:
        counts: dict[str, int] = {}
        for item in getattr(alternative, "items", []) or []:
            label = getattr(item, "speaker", None)
            if not label:
                continue
            counts[label] = counts.get(label, 0) + 1
        raw_label = max(counts, key=counts.get) if counts else None
        friendly = self._speaker_name(job, raw_label)
        return friendly, (raw_label or "spk_unk")

    async def _handle_result(self, job: PocJob, result_id: str, speaker_label: str, raw_label: str, text: str, is_final: bool) -> None:
        entry = job.pending_results.get(result_id)
        if not entry:
            entry = {
                "index": job.next_entry_index,
                "speaker": speaker_label,
                "raw_speaker": raw_label,
                "result_id": result_id,
                "text": text,
                "timestamp": now_iso(),
            }
            job.next_entry_index += 1
            job.pending_results[result_id] = entry
            await job.queue.put({"type": "transcript", "action": "append", "payload": self._public_payload(entry)})
        else:
            if entry["text"] == text and entry["speaker"] == speaker_label:
                if is_final:
                    await self._finalize_result(job, result_id)
                return
            entry["text"] = text
            entry["speaker"] = speaker_label
            entry["raw_speaker"] = raw_label
            await job.queue.put({"type": "transcript", "action": "update", "payload": self._public_payload(entry)})
        if is_final:
            await self._finalize_result(job, result_id)

    async def _finalize_result(self, job: PocJob, result_id: str) -> None:
        entry = job.pending_results.pop(result_id, None)
        if not entry:
            return
        payload = self._public_payload(entry)
        job.transcripts.append(payload)
        await job.queue.put({"type": "transcript", "action": "update", "payload": payload})

    async def _finalize_pending_results(self, job: PocJob) -> None:
        for result_id in list(job.pending_results.keys()):
            await self._finalize_result(job, result_id)

    def _public_payload(self, entry: dict[str, Any]) -> dict[str, Any]:
        return {
            "index": entry["index"],
            "speaker": entry["speaker"],
            "raw_speaker": entry.get("raw_speaker", entry["speaker"]),
            "result_id": entry.get("result_id"),
            "text": entry["text"],
            "timestamp": entry["timestamp"],
        }
