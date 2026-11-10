"""Loopback service for two windows belonging to a single desktop application."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import secrets
import tempfile
import time

import cv2
from fastapi import Depends, FastAPI, Header, HTTPException, Request, UploadFile, WebSocket
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .recognition import CAPTURE_PROFILE
from .session import ClinicSession
from .text_to_sign import TextPlanner
from .playback import load_join_profile
from .speech import SpeechService, stream_dictation
from .language_assist import LanguageAssist
from .avatar_voice import load_avatar_voice
from .multimodal_provider import MultimodalProvider
from .recognition_modes import RecognitionModes, load_catalogs
from .clinic_phrases import quick_phrases


ROOT = Path(__file__).resolve().parents[1]
ASSETS = Path(os.environ.get("CLINIC_ASSETS", str(ROOT / "assets"))).resolve()
FRONTEND = Path(os.environ.get("CLINIC_FRONTEND", str(ROOT / "dist"))).resolve()
TOKEN = os.environ.get("CLINIC_TOKEN", "local-development")
WORDS = json.loads((ASSETS / "vocabulary.json").read_text(encoding="utf-8"))
BANK = json.loads((ASSETS / "motions/manifest.json").read_text(encoding="utf-8"))
PHRASES = json.loads((ASSETS / "phrases.json").read_text(encoding="utf-8"))
SEMANTIC_BANK = json.loads((ASSETS / "semantic_bank.json").read_text(encoding="utf-8"))
MM_SAMPLES = json.loads((ASSETS / "multimodal-samples/manifest.json").read_text(encoding="utf-8"))["entries"]
RECOGNITION_CATALOGS = load_catalogs(ASSETS)
planner = TextPlanner(WORDS, PHRASES, SEMANTIC_BANK)
session = ClinicSession(planner, {entry["id"]: entry["duration_ms"] for entry in BANK["entries"]}, load_join_profile(ASSETS), load_avatar_voice(ASSETS))
engine = None
temp_root = None
control = asyncio.Lock()
speech = SpeechService(ASSETS)
language = LanguageAssist(ASSETS, planner)


@asynccontextmanager
async def lifespan(app):
    global engine, temp_root, speech, language
    language = LanguageAssist(ASSETS, planner)
    if speech.closed:
        speech = SpeechService(ASSETS)
    session.loop = asyncio.get_running_loop()
    engine = RecognitionModes(ASSETS, session.thread_event)
    await run_in_threadpool(engine.warmup)
    temp_root = tempfile.TemporaryDirectory(prefix="vsl-clinic-")
    app.state.started = time.time()
    async def endpoint_clock():
        while True:
            if not session.recognition.get("switching"):
                info = recognition_info()
                if info != session.recognition:
                    session.recognition = info
                    session.changed()
            session.tick()
            await asyncio.sleep(0.1)
    endpoint_task = asyncio.create_task(endpoint_clock())
    try:
        yield
    finally:
        endpoint_task.cancel()
        await asyncio.gather(endpoint_task, return_exceptions=True)
        speech.close()
        await run_in_threadpool(language.close)
        await run_in_threadpool(getattr(engine, "close", engine.stop))
        temp_root.cleanup()


app = FastAPI(title="VSL Clinic", version="0.5.2", lifespan=lifespan, docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"], allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type"])


def authorize(authorization: str | None = Header(default=None)):
    if not authorization or not secrets.compare_digest(authorization, "Bearer " + TOKEN):
        raise HTTPException(401, "Local session token required")


@app.get("/healthcheck")
async def healthcheck():
    model = recognition_info()
    loaded = model.get("worker", {}).get("status") == "ready" if model.get("family") == "multimodal100" else engine is not None
    return {"service": "vsl-clinic", "status": "ok", "version": "0.5.2", "model_loaded": loaded,
            "recognition": model}


def recognition_info():
    if isinstance(engine, RecognitionModes):
        return engine.info()
    if isinstance(engine, MultimodalProvider):
        return engine.info()
    return {"name": "SL-GCN", "labels": 400, "family": "legacy400",
            "sha256": engine.recognizer.sha256 if engine else None, "capture_profile": CAPTURE_PROFILE}


@app.get("/api/bootstrap", dependencies=[Depends(authorize)])
async def bootstrap():
    return {"vocabulary": WORDS, "phrases": planner.entries, "quick_phrases": quick_phrases(planner), "bank": BANK, "avatar_url": "/assets/avatar/ClinicMale.vrm",
            "model": recognition_info(),
            "patient_sources": [w for w in RECOGNITION_CATALOGS[engine.mode] if w["demo"]],
            "recognition_catalogs": RECOGNITION_CATALOGS,
            "speech": speech.info(), "language": language.info(), "state": session.snapshot(), "server_time_ms": time.time() * 1000}


@app.websocket("/ws/speech")
async def speech_socket(socket: WebSocket, token: str = "", live: bool = False):
    if not secrets.compare_digest(token, TOKEN):
        await socket.close(code=1008)
        return
    def record_speech_metric(item):
        if session.conversation["epoch"] != epoch:
            return
        session.metrics.append({**item, "recorded_at_ms": time.time() * 1000})
        session.metrics = session.metrics[-500:]
    epoch = session.conversation["epoch"]
    if live and session.conversation["status"] != "active":
        await socket.close(code=1008)
        return
    def context_id():
        if live:
            return session.session_id + ":" + session.conversation["epoch"]
        return session.session_id
    def receive_transcript(result):
        if live:
            return session.speech_result(result, epoch)
        return None
    await stream_dictation(socket, speech, context_id, record_speech_metric,
                           live=live, on_transcript=receive_transcript,
                           can_accept=lambda: len(session.speech_drafts) < 20)


class TextRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    mode: str = "sign"


@app.post("/api/text/plan", dependencies=[Depends(authorize)])
async def plan(payload: TextRequest):
    try:
        return planner.plan(payload.text)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.post("/api/messages", dependencies=[Depends(authorize)])
async def send(payload: TextRequest):
    try:
        return session.send(payload.text, payload.mode)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@app.post("/api/language/suggest", dependencies=[Depends(authorize)])
async def language_suggestion(payload: TextRequest):
    context = (session.session_id, session.conversation["epoch"])
    result = await run_in_threadpool(language.suggest, payload.text)
    if context != (session.session_id, session.conversation["epoch"]):
        raise HTTPException(409, "Cuộc trao đổi đã thay đổi. Vui lòng nhập lại câu trong phiên mới.")
    return result


async def clear_language_context():
    global language
    previous, language = language, LanguageAssist(ASSETS, planner)
    await run_in_threadpool(previous.close)


class PlaybackRequest(BaseModel):
    action: str
    playback_id: str
    rate: float | None = None
    iteration: int | None = Field(default=None, ge=0)


class AvatarVoiceRequest(BaseModel):
    enabled: bool


@app.post("/api/avatar/voice", dependencies=[Depends(authorize)])
async def avatar_voice(payload: AvatarVoiceRequest):
    session.avatar_voice_enabled = payload.enabled
    session.changed()
    return session.snapshot()


@app.post("/api/playback", dependencies=[Depends(authorize)])
async def playback(payload: PlaybackRequest):
    try:
        session.control_playback(payload.action, payload.playback_id, payload.rate, payload.iteration)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return session.snapshot()


class CaptureRequest(BaseModel):
    kind: str
    demo_id: str | None = None
    camera_index: int = Field(default=0, ge=0, le=8)


class ConversationRequest(BaseModel):
    mode: str = "manual"
    source: CaptureRequest | None = None


class RecognitionModeRequest(BaseModel):
    mode: str


def capture_source(payload):
    if payload.kind == "camera":
        return payload.camera_index
    if payload.kind != "demo":
        raise HTTPException(422, "Chọn camera hoặc video mẫu.")
    words = RECOGNITION_CATALOGS[engine.mode]
    word = next((w for w in words if w["id"] == payload.demo_id and w["demo"]), None)
    if word is None:
        raise HTTPException(422, "Video không thuộc bộ từ đang chọn. Hãy chọn lại video mẫu.")
    return str(ASSETS / word["demo"].removeprefix("/assets/"))


@app.post("/api/recognition/mode", dependencies=[Depends(authorize)])
async def recognition_mode(payload: RecognitionModeRequest):
    if payload.mode not in RECOGNITION_CATALOGS:
        raise HTTPException(422, "Chọn Fusion hoặc Sign only.")
    async with control:
        if engine.mode == payload.mode:
            return session.snapshot()
        old_mode = engine.mode
        request_session = session.session_id
        selected = session.conversation["source"]
        old_word = next((w for w in RECOGNITION_CATALOGS[old_mode] if w["id"] == selected.get("demo_id")), None)
        resume = session.conversation["status"] == "active" or session.capture["status"] in {"starting", "ready", "tracking", "no_person", "signing"}
        uploaded = engine.last_source if engine.last_source and engine.last_source[1] == "video" else None
        engine.generation = max(engine.generation, session.capture.get("generation", 0)) + 1
        session.recognition = dict(engine.info(), switching=True, requested_mode=payload.mode)
        session.capture_stopped(engine.generation)
        try:
            await run_in_threadpool(engine.activate, payload.mode)
            if selected["kind"] == "demo":
                demos = [w for w in RECOGNITION_CATALOGS[payload.mode] if w["demo"]]
                word = next((w for w in demos if old_word and w["label"] == old_word["label"]), demos[0])
                session.conversation["source"] = dict(kind="demo", demo_id=word["id"])
            session.recognition = engine.info()
            session.changed()
            if resume and session.session_id == request_session:
                source, kind = uploaded or (capture_source(CaptureRequest(**session.conversation["source"])), session.conversation["source"]["kind"])
                await run_in_threadpool(engine.start, source, kind)
        except Exception as error:
            session.recognition = dict(engine.info(), switching=False)
            session.capture.update(status="error", message="Chưa đổi được chế độ nhận dạng. Chọn lại chế độ hoặc kiểm tra nguồn hình.")
            session.changed()
            raise HTTPException(503, session.capture["message"]) from error
    return session.snapshot()


@app.post("/api/conversation/configure", dependencies=[Depends(authorize)])
async def configure_conversation(payload: ConversationRequest):
    async with control:
        try:
            if payload.source:
                capture_source(payload.source)
            session.configure_conversation(payload.mode, payload.source.model_dump() if payload.source else None)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
    return session.snapshot()


@app.post("/api/conversation/start", dependencies=[Depends(authorize)])
async def start_conversation():
    if session.conversation["status"] != "active":
        await start_capture(CaptureRequest(**session.conversation["source"]))
        session.start_conversation()
    return session.snapshot()


class EndConversationRequest(BaseModel):
    keep_temporary: bool = False


@app.post("/api/conversation/stop", dependencies=[Depends(authorize)])
async def stop_conversation(payload: EndConversationRequest = EndConversationRequest()):
    # End is visible immediately even if the other window is loading a provider.
    # The mode request checks the session identity before restarting capture.
    engine.generation = max(engine.generation, session.capture.get("generation", 0)) + 1
    session.stop_conversation(payload.keep_temporary, engine.generation)
    async with control:
        await clear_language_context()
        await run_in_threadpool(engine.stop)
    return session.snapshot()


@app.get("/api/session/temporary", dependencies=[Depends(authorize)])
async def temporary_conversation():
    # One optional read-only copy in process memory; never persisted to disk.
    return session.temporary


@app.post("/api/session/temporary/discard", dependencies=[Depends(authorize)])
async def discard_temporary_conversation():
    session.discard_temporary()
    return session.snapshot()


class SpeechReviewRequest(BaseModel):
    draft_id: str
    text: str | None = Field(default=None, min_length=1, max_length=500)
    mode: str = "sign"


@app.post("/api/speech/review", dependencies=[Depends(authorize)])
async def review_speech(payload: SpeechReviewRequest):
    try:
        session.review_speech(payload.draft_id, payload.text, payload.mode)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return session.snapshot()


@app.post("/api/capture/start", dependencies=[Depends(authorize)])
async def start_capture(payload: CaptureRequest):
    async with control:
        source = capture_source(payload)
        generation = await run_in_threadpool(engine.start, source, payload.kind)
        session.conversation["source"] = payload.model_dump()
        session.changed()
    return {"generation": generation}


@app.post("/api/capture/upload", dependencies=[Depends(authorize)])
async def upload_video(file: UploadFile):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp4", ".mov", ".avi", ".mkv"}:
        raise HTTPException(422, "Chọn video MP4, MOV, AVI hoặc MKV.")
    path = Path(temp_root.name) / (secrets.token_hex(12) + suffix)
    total = 0
    try:
        with path.open("wb") as output:
            while block := await file.read(1024 * 1024):
                total += len(block)
                if total > 100 * 1024 * 1024:
                    raise HTTPException(413, "Video vượt quá 100 MB.")
                output.write(block)
        cap = cv2.VideoCapture(str(path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        readable = cap.isOpened()
        cap.release()
        if not readable or fps <= 0 or frames <= 0 or frames / fps > 180:
            raise HTTPException(422, "Video không đọc được hoặc dài quá 3 phút.")
        async with control:
            generation = await run_in_threadpool(engine.start, str(path), "video")
        return {"generation": generation, "bytes": total, "duration_seconds": frames / fps}
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()


@app.post("/api/capture/stop", dependencies=[Depends(authorize)])
async def stop_capture():
    async with control:
        await run_in_threadpool(engine.stop)
        engine.generation += 1
        session.capture_stopped(engine.generation)
    return session.snapshot()


@app.get("/api/preview")
async def preview(request: Request, token: str):
    if not secrets.compare_digest(token, TOKEN):
        raise HTTPException(401)
    async def frames():
        last_version = -1
        while not await request.is_disconnected():
            version, data = engine.preview_frame()
            if version != last_version and data:
                last_version = version
                yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + str(len(data)).encode() + b"\r\n\r\n" + data + b"\r\n"
            await asyncio.sleep(0.04)
    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame", headers={"Cache-Control": "no-store"})


class ConfirmRequest(BaseModel):
    message_id: str
    text: str = Field(min_length=1, max_length=500)


@app.post("/api/confirm", dependencies=[Depends(authorize)])
async def confirm(payload: ConfirmRequest):
    try:
        session.confirm(payload.message_id, payload.text)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return session.snapshot()


class FeedbackRequest(BaseModel):
    value: str


@app.post("/api/feedback", dependencies=[Depends(authorize)])
async def feedback(payload: FeedbackRequest):
    try:
        session.feedback(payload.value)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return session.snapshot()


@app.post("/api/session/reset", dependencies=[Depends(authorize)])
async def reset_session():
    async with control:
        engine.generation = max(engine.generation, session.capture.get("generation", 0)) + 1
        session.reset(generation=engine.generation, preserve_temporary=True)
        await clear_language_context()
        await run_in_threadpool(engine.stop)
    return session.snapshot()


@app.post("/api/metrics", dependencies=[Depends(authorize)])
async def metric(payload: dict):
    allowed = {key: payload[key] for key in ("event", "message_id", "playback_id", "received_at_ms", "painted_at_ms", "revision", "role",
                                            "iteration", "renderer_frames", "measured_fps", "mean_cpu_ms", "max_frame_gap_ms") if key in payload}
    session.metrics.append({**allowed, "recorded_at_ms": time.time() * 1000})
    session.metrics = session.metrics[-500:]
    return {"ok": True}


@app.get("/api/diagnostics", dependencies=[Depends(authorize)])
async def diagnostics():
    model = recognition_info()
    return {"model_sha256": model["sha256"], "capture_profile": model["capture_profile"], "model": model,
            "state": session.snapshot(), "metrics": session.metrics,
            "uptime_seconds": time.time() - app.state.started}


@app.post("/api/shutdown", dependencies=[Depends(authorize)])
async def shutdown():
    await stop_capture()
    callback = getattr(app.state, "request_shutdown", None)
    if callback:
        asyncio.get_running_loop().call_later(0.2, callback)
    return {"ok": True}


@app.websocket("/ws")
async def websocket(socket: WebSocket, role: str = "doctor", token: str = ""):
    if role not in {"doctor", "patient"} or not secrets.compare_digest(token, TOKEN):
        await socket.close(code=1008)
        return
    await socket.accept()
    channel = asyncio.Queue(maxsize=1)
    client_id = secrets.token_hex(8)
    session.listeners[client_id] = (role, channel)
    session.changed()
    async def read_until_disconnect():
        while True:
            await socket.receive_text()
    async def send_snapshots():
        while True:
            try:
                state = await asyncio.wait_for(channel.get(), timeout=15)
            except asyncio.TimeoutError:
                state = session.snapshot()
            await socket.send_json({"type": "snapshot", "state": state})
    tasks = [asyncio.create_task(read_until_disconnect()), asyncio.create_task(send_snapshots())]
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        session.listeners.pop(client_id, None)
        if role == "patient" and not any(item[0] == "patient" for item in session.listeners.values()):
            session.patient_disconnected()
        session.changed()


app.mount("/assets", StaticFiles(directory=ASSETS), name="assets")
if (FRONTEND / "ui-assets").is_dir():
    app.mount("/ui-assets", StaticFiles(directory=FRONTEND / "ui-assets"), name="ui-assets")
if (FRONTEND / "fonts").is_dir():
    app.mount("/fonts", StaticFiles(directory=FRONTEND / "fonts"), name="fonts")
if (FRONTEND / "audio").is_dir():
    app.mount("/audio", StaticFiles(directory=FRONTEND / "audio"), name="audio")


@app.get("/{page:path}")
async def index(page: str):
    if page not in {"", "doctor", "patient", "index.html"}:
        raise HTTPException(404)
    if not (FRONTEND / "index.html").is_file():
        return {"service": "vsl-clinic", "message": "Run npm run build to open the desktop UI."}
    return FileResponse(FRONTEND / "index.html", headers={"Cache-Control": "no-store"})
