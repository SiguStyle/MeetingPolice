from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect

from .controller import POCController

router = APIRouter()
controller = POCController()


@router.post("/start")
async def start_poc_run(
    agenda: UploadFile | None = File(None),
    audio: UploadFile | None = File(None),
):
    if audio is None:
        raise HTTPException(status_code=400, detail="音声ファイルを指定してください")

    agenda_bytes = await agenda.read() if agenda else b""
    audio_bytes = await audio.read()
    agenda_text = agenda_bytes.decode("utf-8", errors="ignore")
    job_id = await controller.start_transcription(agenda_text=agenda_text, audio_filename=audio.filename or "audio", audio_bytes=audio_bytes)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}")
async def get_poc_job(job_id: str):
    try:
        return controller.get_job_payload(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません") from exc


@router.post("/jobs/{job_id}/analyze")
async def analyze_poc_job(job_id: str):
    try:
        return await controller.analyze_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/jobs/{job_id}/classify")
async def classify_poc_job(job_id: str, refresh: bool = False):
    try:
        segments = await controller.classify_job(job_id, refresh=refresh)
        return {"job_id": job_id, "classified_segments": segments}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.websocket("/ws/{job_id}")
async def poc_stream(websocket: WebSocket, job_id: str):
    await websocket.accept()
    job = controller.get_job(job_id)
    if not job:
        await websocket.send_json({"type": "error", "message": "ジョブが見つかりません"})
        await websocket.close(code=4404)
        return

    # Send backlog
    for payload in job.transcripts:
        payload = dict(payload)
        payload.setdefault("raw_speaker", payload.get("speaker", "spk_unk"))
        payload.setdefault("result_id", f"historical-{payload.get('index', 0)}")
        await websocket.send_json({"type": "transcript", "action": "append", "payload": payload})
    for entry in sorted(job.pending_results.values(), key=lambda item: item["index"]):
        payload = {
            "index": entry["index"],
            "speaker": entry["speaker"],
            "raw_speaker": entry.get("raw_speaker", entry["speaker"]),
            "text": entry["text"],
            "timestamp": entry["timestamp"],
            "result_id": entry.get("result_id"),
        }
        await websocket.send_json({"type": "transcript", "action": "append", "payload": payload})
    if job.classified_segments:
        await websocket.send_json({"type": "classification", "payload": job.classified_segments})
    if job.status == "completed":
        await websocket.send_json({"type": "complete"})
        await websocket.close()
        return

    try:
        while True:
            message = await job.queue.get()
            await websocket.send_json(message)
            if message.get("type") == "complete":
                await websocket.close()
                break
    except WebSocketDisconnect:
        return
