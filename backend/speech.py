"""Bounded, offline Vietnamese dictation. Audio is kept in RAM only."""
from __future__ import annotations

import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import threading
import time
import uuid

import numpy as np
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
from .speech_activity import FRAME_BYTES, FRAME_MS, FRAME_SAMPLES, SAMPLE_RATE, SpeechActivity

MAX_UTTERANCE_FRAMES = 375
END_SILENCE_FRAMES = 18


class UtteranceSegmenter:
    """32 ms neural speech gate, 320 ms pre-roll, 576 ms endpoint, 12 s ceiling."""

    def __init__(self, vad=None):
        self.vad = vad or SpeechActivity()
        self.tail = bytearray()
        self.pre_roll = deque(maxlen=10)
        self.votes = deque(maxlen=5)
        self.frames = []
        self.voiced = 0
        self.silence = 0
        self.total_samples = 0
        self.last_voice_sample = 0
        self.wait_for_pause = False
        self.rearm_silence = 0

    def feed(self, data: bytes) -> list[dict]:
        if len(data) % 2 or len(data) > SAMPLE_RATE:
            raise ValueError("Gói âm thanh không hợp lệ.")
        self.tail.extend(data)
        utterances = []
        while len(self.tail) >= FRAME_BYTES:
            frame = bytes(self.tail[:FRAME_BYTES])
            del self.tail[:FRAME_BYTES]
            self.total_samples += FRAME_SAMPLES
            voiced = self.vad.is_speech(frame, SAMPLE_RATE)
            if self.wait_for_pause:
                self.rearm_silence = 0 if voiced else self.rearm_silence + 1
                if self.rearm_silence >= END_SILENCE_FRAMES:
                    self.wait_for_pause = False
                continue
            if voiced:
                self.last_voice_sample = self.total_samples
            if not self.frames:
                self.pre_roll.append(frame)
                self.votes.append(voiced)
                if sum(self.votes) >= 3:
                    self.frames = list(self.pre_roll)
                    self.voiced = sum(self.votes)
                    self.pre_roll.clear()
                    self.votes.clear()
                continue
            self.frames.append(frame)
            self.voiced += int(voiced)
            self.silence = 0 if voiced else self.silence + 1
            if self.silence >= END_SILENCE_FRAMES or len(self.frames) >= MAX_UTTERANCE_FRAMES:
                reached_limit = len(self.frames) >= MAX_UTTERANCE_FRAMES
                item = self.flush()
                # A ceiling is not a new speech onset. Require an actual pause
                # before accepting another turn, including sustained interference.
                self.wait_for_pause = reached_limit
                self.rearm_silence = 0
                if item:
                    utterances.append(item)
        return utterances

    def flush(self) -> dict | None:
        item = None
        if self.frames and self.voiced >= 6:
            item = {
                "pcm": b"".join(self.frames),
                "duration_ms": sum(len(frame) for frame in self.frames) * 1000 / (SAMPLE_RATE * 2),
                "voice_end_sample": self.last_voice_sample,
                "endpoint_audio_ms": (self.total_samples - self.last_voice_sample) * 1000 / SAMPLE_RATE,
                "cut_at_limit": len(self.frames) >= MAX_UTTERANCE_FRAMES,
            }
        self.frames = []
        self.voiced = 0
        self.silence = 0
        self.pre_roll.clear()
        self.votes.clear()
        return item

    def finish(self) -> dict | None:
        # Keep the last partial worklet packet when the doctor presses Stop.
        if self.tail and self.frames:
            frame = bytes(self.tail)
            self.tail.clear()
            self.frames.append(frame)
        return self.flush()


class SpeechService:
    def __init__(self, assets: Path):
        self.path = assets / "speech/phowhisper-base-int8"
        self.model = None
        self._model_lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="clinic-speech")
        self.active_id = None
        self.closed = False

    def info(self) -> dict:
        return {
            "available": (self.path / "model.bin").is_file(),
            "loaded": self.model is not None,
            "name": "PhoWhisper base INT8",
            "language": "vi",
            "device": "cpu",
            "cpu_threads": 2,
            "sample_rate": SAMPLE_RATE,
            "endpoint_ms": END_SILENCE_FRAMES * FRAME_MS,
            "activity_detector": "Silero v6 ONNX streaming",
        }

    def prepare(self):
        with self._model_lock:
            if self.model is None:
                if not self.info()["available"]:
                    raise RuntimeError("Thiếu bộ nhận giọng nói. Cài gói giọng nói cục bộ trước khi dùng micro.")
                from faster_whisper import WhisperModel
                self.model = WhisperModel(
                    str(self.path), device="cpu", compute_type="int8",
                    cpu_threads=2, num_workers=1, local_files_only=True,
                )
                from faster_whisper.vad import get_vad_model
                get_vad_model()

    def transcribe(self, pcm: bytes) -> dict:
        self.prepare()
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768
        if not 1600 <= samples.size <= SAMPLE_RATE * 13:
            raise ValueError("Mỗi ý nói phải dài từ 0,1 đến 13 giây.")
        start = time.perf_counter()
        if float(np.sqrt(np.mean(samples * samples))) < 0.0003:
            return {"text": "", "decode_ms": 0, "audio_ms": samples.size * 1000 / SAMPLE_RATE,
                    "uncertain": True, "segments": []}
        segments, _ = self.model.transcribe(
            samples, language="vi", task="transcribe", beam_size=3,
            temperature=0.0, condition_on_previous_text=False,
            without_timestamps=True, vad_filter=False,
            max_new_tokens=160,
        )
        records = list(segments)
        accepted = [part for part in records if not (part.no_speech_prob > 0.65 and part.avg_logprob < -0.7)]
        text = " ".join(part.text.strip() for part in accepted).strip()
        return {
            "text": text,
            "decode_ms": (time.perf_counter() - start) * 1000,
            "audio_ms": samples.size * 1000 / SAMPLE_RATE,
            "uncertain": not accepted or any(part.avg_logprob < -0.85 or part.compression_ratio > 2.4 for part in accepted),
            "segments": [{"avg_logprob": part.avg_logprob, "no_speech_prob": part.no_speech_prob} for part in records],
        }

    async def run(self, function, *args):
        if self.closed:
            raise RuntimeError("Bộ giọng nói đã dừng.")
        return await asyncio.get_running_loop().run_in_executor(self.executor, function, *args)

    def close(self):
        self.closed = True
        self.active_id = None
        self.executor.shutdown(wait=False, cancel_futures=True)


async def stream_dictation(socket: WebSocket, service: SpeechService, session_id, record_metric,
                           live=False, on_transcript=None, can_accept=lambda: True):
    """One doctor microphone; no silent drops when the decoder falls behind."""
    await socket.accept()
    if service.active_id is not None:
        await socket.send_json({"type": "error", "message": "Một micro khác đang hoạt động. Hãy dừng micro đó trước."})
        await socket.close(code=1013)
        return
    owner = uuid.uuid4().hex
    service.active_id = owner
    generation = session_id()
    queue = asyncio.Queue(maxsize=2)
    segmenter = UtteranceSegmenter()
    send_lock = asyncio.Lock()
    cancelled = False
    started = time.perf_counter()
    received_audio = False
    sequence = 0

    def valid():
        return not cancelled and service.active_id == owner and session_id() == generation

    async def emit(data):
        if valid():
            async with send_lock:
                await socket.send_json(data)

    async def enqueue(item):
        if not item:
            return
        if queue.full():
            raise ValueError("Máy đang xử lý chậm. Bản ghi đã dừng; hãy kiểm tra phần chữ đã nhận và nói lại ý còn thiếu.")
        item["queued_at"] = time.perf_counter()
        queue.put_nowait(item)

    async def decode():
        nonlocal sequence
        while True:
            item = await queue.get()
            try:
                if item is None:
                    return
                if not valid():
                    return
                await emit({"type": "decoding"})
                queue_ms = (time.perf_counter() - item["queued_at"]) * 1000
                result = await service.run(service.transcribe, item["pcm"])
                if not valid():
                    return
                if not result['text'].strip():
                    await emit({'type': 'speech_rejected', 'message': 'Chưa nghe rõ lời nói. Bạn hãy nói lại gần micro hơn.'})
                    record_metric({'type': 'speech_rejected', 'decode_ms': result['decode_ms'], 'audio_ms': result['audio_ms']})
                    continue
                sequence += 1
                result.update({
                    "type": "transcript", "sequence": sequence,
                    "utterance_id": f"{owner}:{sequence}",
                    "session_id": generation, "queue_ms": queue_ms,
                    "endpoint_audio_ms": item["endpoint_audio_ms"],
                    "cut_at_limit": item["cut_at_limit"],
                })
                if on_transcript:
                    result["delivery"] = on_transcript(result)
                await emit(result)
                record_metric({
                    "type": "speech", "decode_ms": result["decode_ms"],
                    "queue_ms": queue_ms, "audio_ms": result["audio_ms"],
                    "endpoint_audio_ms": item["endpoint_audio_ms"],
                    "characters": len(result["text"]),
                    "cut_at_limit": item["cut_at_limit"],
                    "delivery": (result.get('delivery') or {}).get('status'),
                })
            finally:
                queue.task_done()

    worker = None
    reader = None
    try:
        await emit({"type": "loading"})
        await service.run(service.prepare)
        started = time.perf_counter()
        await emit({"type": "ready", **service.info()})
        worker = asyncio.create_task(decode())
        while valid():
            reader = asyncio.create_task(socket.receive())
            done, _ = await asyncio.wait({reader, worker}, timeout=1, return_when=asyncio.FIRST_COMPLETED)
            while not done and valid():
                if not live and time.perf_counter() - started > 90:
                    raise ValueError("Đã đủ 90 giây. Kiểm tra nội dung rồi bật micro để nói tiếp.")
                done, _ = await asyncio.wait({reader, worker}, timeout=1, return_when=asyncio.FIRST_COMPLETED)
            if not valid():
                break
            if worker in done:
                await worker
                break
            packet = reader.result()
            reader = None
            if packet["type"] == "websocket.disconnect":
                break
            binary = packet.get("bytes")
            if binary is not None:
                if not received_audio:
                    started = time.perf_counter()
                    received_audio = True
                if not live and time.perf_counter() - started > 90:
                    raise ValueError("Đã đủ 90 giây. Kiểm tra nội dung rồi bật micro để nói tiếp.")
                if not can_accept():
                    raise ValueError("Đã có 20 câu chờ xác nhận. Micro đã dừng; hãy xử lý các câu này rồi bật lại.")
                for item in segmenter.feed(binary):
                    await enqueue(item)
            elif packet.get("text"):
                command = json.loads(packet["text"])
                if command.get("action") == "finish":
                    await enqueue(segmenter.finish())
                    # Race the sentinel against worker failure, so a failed
                    # decoder cannot leave a full queue waiting forever.
                    ending = asyncio.create_task(queue.put(None))
                    try:
                        done, _ = await asyncio.wait({ending, worker}, return_when=asyncio.FIRST_COMPLETED)
                        if worker in done:
                            await worker
                        await ending
                    finally:
                        ending.cancel()
                    await worker
                    await emit({"type": "finished"})
                    break
                if command.get("action") == "cancel":
                    cancelled = True
                    break
                raise ValueError("Lệnh micro không hợp lệ.")
    except WebSocketDisconnect:
        pass
    except Exception as error:
        try:
            await emit({"type": "error", "message": str(error)[:250]})
        except (WebSocketDisconnect, RuntimeError):
            pass
    finally:
        cancelled = True
        if reader is not None:
            reader.cancel()
            await asyncio.gather(reader, return_exceptions=True)
        if worker is not None:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
        if service.active_id == owner:
            service.active_id = None
        try:
            await socket.close()
        except RuntimeError:
            pass
