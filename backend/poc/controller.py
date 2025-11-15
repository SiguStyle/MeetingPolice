from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from services.bedrock_utils import summarize_transcript
from services.comprehend_utils import analyze_sentiment
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


class POCController:
    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or Path(__file__).resolve().parents[1] / "data" / "poc"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, PocJob] = {}

    async def start_transcription(self, agenda_text: str, audio_filename: str, audio_bytes: bytes) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = PocJob(job_id=job_id, agenda_text=agenda_text, audio_filename=audio_filename)
        self.jobs[job_id] = job

        job_dir = self._job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "agenda.txt").write_text(agenda_text, encoding="utf-8")
        (job_dir / "audio.bin").write_bytes(audio_bytes)

        asyncio.create_task(self._simulate_stream(job))
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

    async def _simulate_stream(self, job: PocJob) -> None:
        script = self._build_script(job)
        job_dir = self._job_dir(job.job_id)
        transcript_path = job_dir / "transcripts.json"
        for idx, line in enumerate(script, start=1):
            payload = {
                "index": idx,
                "speaker": "Speaker A" if idx % 2 else "Speaker B",
                "text": line,
                "timestamp": now_iso(),
            }
            job.transcripts.append(payload)
            await job.queue.put({"type": "transcript", "payload": payload})
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
