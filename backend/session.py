"""One authoritative conversation and playback clock shared by both windows."""
from __future__ import annotations

import copy
import time
import uuid
from collections import deque

from .text_to_sign import TextPlanner
from .playback import build_timeline
from .patient_turns import PatientTurns
from .patient_handover import PatientHandover
from .avatar_voice import attach_narration
from .speech_repair import repair_speech


def now_ms():
    return time.time() * 1000


def identity():
    return uuid.uuid4().hex[:12]


class ClinicSession:
    def __init__(self, planner: TextPlanner, durations: dict[str, float], join_profile: dict | None = None, voice_bank=None):
        self.planner = planner
        self.durations = durations
        self.join_profile = join_profile or {}
        self.voice_bank = voice_bank or {}
        self.listeners = {}
        self.loop = None
        self.revision = 0
        self.metrics = []
        self.reset()

    def reset(self, *, generation=None, preserve_temporary=False):
        if not preserve_temporary:
            self.temporary = None
        generation = self.capture.get("generation", 0) if generation is None and hasattr(self, "capture") else (generation or 0)
        self.session_id = identity()
        self.messages = []
        self.capture = {"status": "idle", "generation": generation}
        self.playback = None
        self.pending = []
        self.current_result = None
        self.recognition_seen = deque(maxlen=512)
        self.recognition_sequence = None
        self.turns = PatientTurns()
        self.handover = PatientHandover()
        self.conversation = {"status": "idle", "mode": "manual", "epoch": identity(),
                             "source": {"kind": "camera", "camera_index": 0}, "started_at_ms": None}
        self.speech_drafts = []
        self.speech_seen = set()
        self.avatar_voice_enabled = getattr(self, "avatar_voice_enabled", True)
        self.recognition = getattr(self, "recognition", {"mode": "fusion", "labels": 100, "status": "loading", "switching": False})
        self.metrics.clear()
        self.revision += 1
        self.broadcast()

    def snapshot(self):
        return {
            "session_id": self.session_id, "revision": self.revision,
            "server_time_ms": now_ms(), "messages": copy.deepcopy(self.messages),
            "capture": dict(self.capture), "current_result": copy.deepcopy(self.current_result),
            "playback": copy.deepcopy(self.playback), "pending_count": len(self.pending),
            "clients": {role: sum(item[0] == role for item in self.listeners.values()) for role in ("doctor", "patient")},
            "conversation": copy.deepcopy(self.conversation),
            "patient_turn": copy.deepcopy(self.turns.current),
            "speech_drafts": copy.deepcopy(self.speech_drafts),
            "avatar_voice_enabled": self.avatar_voice_enabled,
            "recognition": copy.deepcopy(self.recognition),
            "temporary": ({"id": self.temporary["id"], "saved_at_ms": self.temporary["saved_at_ms"],
                           "message_count": len(self.temporary["messages"]), "draft_count": len(self.temporary["speech_drafts"])}
                          if self.temporary else None),
        }

    def broadcast(self):
        payload = self.snapshot()
        for _, channel in self.listeners.values():
            if channel.full():
                channel.get_nowait()
            channel.put_nowait(payload)

    def changed(self):
        self.revision += 1
        self.broadcast()

    def thread_event(self, event):
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.capture_event, event)

    def capture_event(self, event):
        generation = event.get("generation", 0)
        if generation < self.capture.get("generation", 0):
            return
        if event["type"] == "capture":
            if generation > self.capture.get("generation", 0):
                self.turns.finish(now_ms(), "source_changed")
                self.current_result = None
                self.capture = {}
            self.capture = {**self.capture, **event}
            if event["status"] == "signing":
                self.turns.activity(now_ms())
                self.capture.pop("quality_warning", None)
            if event["status"] in {"error", "idle", "no_person", "starting"}:
                self.current_result = None
            self.handover.observe(self.playback, self.capture, self.conversation["mode"] == "auto", self.elapsed, now_ms())
        elif event["type"] == "recognition_unavailable":
            self.capture["quality_warning"] = event.get("quality_warning") or event.get("policy", {}).get("prompt")
            self.current_result = None
            self.metrics.append({**event, "recorded_at_ms": now_ms()})
            self.metrics = self.metrics[-500:]
        elif event["type"] == "recognition":
            if event.get("stream_id") is not None and event.get("segment_number") is not None:
                stream_key = (generation, event["stream_id"])
                previous = self.recognition_sequence
                if previous and previous[0] == stream_key and event["segment_number"] <= previous[1]:
                    return
                self.recognition_sequence = (stream_key, event["segment_number"])
            segment_key = (generation, event.get("segment_id"))
            if event.get("segment_id"):
                if segment_key in self.recognition_seen:
                    return
                self.recognition_seen.append(segment_key)
            predictions = event["predictions"]
            last_doctor = next((item for item in reversed(self.messages)
                                if item["role"] == "doctor" and item.get("presented_at_ms")), {})
            recent = now_ms() - last_doctor.get("presented_at_ms", 0) < 60000
            question_id = last_doctor.get("phrase_id")
            if last_doctor.get("mode") == "sign" and self.playback and self.playback["message_id"] == last_doctor.get("id"):
                shown = [clause for clause in self.playback["clauses"] if clause["start_ms"] <= self.elapsed()]
                question_id = shown[-1].get("phrase_id") if shown else None
            multimodal = event.get("engine_family") == "multimodal100"
            # Lexical matches have not established motion equivalence to the
            # avatar bank. Do not pass new W IDs into legacy context routing.
            context = [] if multimodal else self.planner.contextual_candidates(predictions, question_id if recent else None)
            top = predictions[0] if predictions else {"gloss": "Chưa nhận rõ", "score": 0}
            uncertain = (not event.get("policy", {}).get("committed", False) if multimodal
                         else top["score"] < 0.55 or bool(event.get("quality_warning")))
            message = {
                "id": identity(), "role": "patient", "text": top["gloss"],
                "created_at_ms": now_ms(), "status": "candidate", "confidence": top["score"],
                "uncertain": uncertain, "predictions": predictions,
                "voice_key": top.get("voice_key"), "original_gloss": top.get("original_gloss", top["gloss"]),
                "recognition": {key: event.get(key) for key in ("engine_family", "contract", "actual_mode", "segment_id", "policy")},
                "quality_warning": event.get("quality_warning"),
                "context_candidates": context,
                "metrics": {key: value for key, value in event.items() if key not in {"predictions", "type"}},
            }
            turn = self.turns.append(message, now_ms())
            if not any(item["id"] == turn["id"] for item in self.messages):
                self.messages.append(turn)
            self.messages = self.messages[-100:]
            self.current_result = message
            self.capture.pop("quality_warning", None)
            if not message["uncertain"] and self.conversation["mode"] == "auto" and self.playback and (self.playback["status"] == "playing" or self.playback.get("pause_reason") == "patient_activity"):
                self.playback["elapsed_ms"] = self.elapsed()
                self.playback["status"] = "paused"
                self.playback["pause_reason"] = "patient_reply"
            self.metrics.append({"type": "recognition", "message_id": message["id"], **event})
            self.metrics = self.metrics[-500:]
        self.changed()

    def capture_stopped(self, generation):
        self.turns.finish(now_ms(), "capture_stopped")
        self.capture = {"status": "idle", "generation": generation}
        self.current_result = None
        self.changed()

    def tick(self):
        turn_changed = self.turns.tick(now_ms(), self.capture)
        handover_changed = self.handover.settle(self.playback, self.capture, now_ms())
        if turn_changed or handover_changed:
            self.changed()

    def configure_conversation(self, mode: str, source: dict | None = None):
        if mode not in {"auto", "manual"}:
            raise ValueError("Chọn Tự động hoặc Xác nhận trước khi gửi.")
        if mode != self.conversation["mode"]:
            self.conversation["epoch"] = identity()
        self.conversation["mode"] = mode
        if source is not None:
            self.conversation["source"] = source
        self.changed()

    def start_conversation(self):
        self.conversation.update(status="active", epoch=identity(), started_at_ms=now_ms())
        self.changed()

    def stop_conversation(self, keep_temporary=False, generation=None):
        mode, source = self.conversation["mode"], copy.deepcopy(self.conversation["source"])
        self.turns.finish(now_ms(), "conversation_stopped")
        for message in self.messages:
            if message["role"] == "doctor" and message["status"] in {"queued", "presenting", "playing", "loading"}:
                message["status"] = "cancelled"
        self.temporary = ({"id": identity(), "saved_at_ms": now_ms(),
                           "messages": copy.deepcopy(self.messages), "speech_drafts": copy.deepcopy(self.speech_drafts)}
                          if keep_temporary and (self.messages or self.speech_drafts) else None)
        # Fence queued camera results before yielding to worker shutdown. Both
        # the session ID and ASR epoch change, so old callbacks cannot repopulate it.
        floor = max(self.capture.get("generation", 0) + 1, generation or 0)
        self.reset(generation=floor, preserve_temporary=True)
        self.conversation.update(mode=mode, source=source)
        self.changed()

    def discard_temporary(self):
        self.temporary = None
        self.changed()

    def speech_result(self, result: dict, epoch: str):
        if self.conversation["status"] != "active" or self.conversation["epoch"] != epoch:
            return None
        key = result["utterance_id"]
        if key in self.speech_seen or not result["text"].strip():
            return None
        self.speech_seen.add(key)
        spoken_text, repair = repair_speech(result)
        try:
            plan = self.planner.plan(spoken_text)
        except ValueError:
            plan = {"supported": False, "unsupported": []}
        reason = ""
        reason_code = "manual"
        if result.get("uncertain") or result.get("cut_at_limit"):
            reason_code = "unclear"
            reason = "Chưa nghe rõ hoặc câu quá dài. Bạn hãy nói lại từng ý ngắn, ngắt một nhịp giữa các ý."
        elif not plan["supported"]:
            reason_code = "unsupported"
            reason = "Chưa có đủ ký hiệu hoặc mẫu câu này. Bạn hãy nói lại bằng câu ngắn hơn, hoặc chọn câu có sẵn."
        elif self.conversation["mode"] == "auto":
            try:
                message = self.send(spoken_text, "sign")
                message["speech_utterance_id"] = key
                if repair:
                    message["raw_text"] = result["text"]
                    message["speech_repair"] = repair
                    self.changed()
                return {"status": "sent", "message_id": message["id"], "repair": repair, "text": spoken_text}
            except ValueError as error:
                reason = str(error)
                reason_code = "busy"
        draft = {"id": key, "text": spoken_text, "raw_text": result["text"], "repair": repair, "created_at_ms": now_ms(),
                 "reason": reason or "Kiểm tra nội dung rồi gửi.", "supported": plan["supported"],
                 "reason_code": reason_code,
                 "unsupported": list(dict.fromkeys(item["text"] for item in plan.get("unsupported", [])))}
        self.speech_drafts.append(draft)
        # Unsent speech is not silently discarded. Stop accepting before overflow.
        self.changed()
        return {"status": "review", "draft_id": key}

    def review_speech(self, draft_id: str, text: str | None, mode: str = "sign"):
        draft = next((item for item in self.speech_drafts if item["id"] == draft_id), None)
        if draft is None:
            raise ValueError("Câu này đã được gửi hoặc bỏ qua.")
        message = self.send(text, mode) if text is not None else None
        self.speech_drafts.remove(draft)
        self.changed()
        return message

    def send(self, text: str, mode: str):
        plan = self.planner.plan(text)
        if mode not in {"sign", "text"}:
            raise ValueError("Unknown message mode")
        if mode == "sign" and not plan["supported"]:
            raise ValueError(plan["message"])
        if mode == "sign" and len(self.pending) >= 6:
            raise ValueError("Đã có 6 nội dung đang chờ. Vui lòng chờ phát xong.")
        message = {"id": identity(), "role": "doctor", "text": plan["text"], "created_at_ms": now_ms(),
                   "mode": mode, "glosses": plan["glosses"], "status": "sent",
                   "phrase_id": plan.get("phrase_id"), "nonmanual": plan.get("nonmanual", "neutral"),
                   "act": plan.get("act", "sequence"), "clauses": plan.get("clauses", [])}
        if mode == "text":
            message["presented_at_ms"] = now_ms()
        self.messages.append(message)
        self.messages = self.messages[-100:]
        if mode == "sign":
            if self.playback and self.playback["status"] not in {"completed", "stopped"}:
                self.pending.append(message)
                message["status"] = "queued"
            else:
                self._start_playback(message)
        self.changed()
        return message

    def _start_playback(self, message):
        timing = build_timeline(message["glosses"], message.get("clauses", []), self.durations, self.join_profile)
        timing = attach_narration(timing, message["glosses"], self.voice_bank)
        self.playback = {"id": identity(), "message_id": message["id"], "text": message["text"],
                         "glosses": message["glosses"], "status": "loading", "rate": 1.0,
                         "elapsed_ms": 0, "started_at_ms": 0, **timing, "iteration": 0,
                         "nonmanual": message.get("nonmanual", "neutral"), "act": message.get("act", "sequence"),
                         "requested_at_ms": now_ms()}
        message["status"] = "presenting"

    def elapsed(self):
        if not self.playback:
            return 0
        elapsed = self.playback["elapsed_ms"]
        if self.playback["status"] == "playing":
            elapsed += (now_ms() - self.playback["started_at_ms"]) * self.playback["rate"]
        return min(self.playback["total_ms"], max(0, elapsed))

    def patient_disconnected(self):
        if self.playback and self.playback["status"] == "playing":
            self.playback["elapsed_ms"] = self.elapsed()
            self.playback["status"] = "paused"
            self.playback["pause_reason"] = "patient_disconnected"
            self.changed()

    def control_playback(self, action: str, playback_id: str, rate: float | None = None, iteration: int | None = None):
        if action not in {"ready", "pause", "resume", "replay", "speed", "complete", "stop"}:
            raise ValueError("Unknown playback action")
        playback = self.playback
        if not playback or playback["id"] != playback_id:
            return
        if action == "ready" and iteration is not None and iteration != playback["iteration"]:
            return
        if action == "complete" and (iteration != playback["iteration"] or playback["status"] != "playing"
                                     or self.elapsed() < playback["total_ms"] - 100):
            return
        if action == "ready" and playback["status"] == "loading":
            playback["status"] = "playing"
            playback["started_at_ms"] = now_ms()
            message = next((item for item in self.messages if item["id"] == playback["message_id"]), None)
            if message:
                message["presented_at_ms"] = now_ms()
        elif action == "pause" and playback["status"] == "playing":
            playback["elapsed_ms"] = self.elapsed()
            playback["status"] = "paused"
        elif action == "resume" and playback["status"] == "paused":
            self.handover.manual()
            playback["started_at_ms"] = now_ms()
            playback["status"] = "playing"
            playback.pop("pause_reason", None)
        elif action == "replay":
            playback["elapsed_ms"] = 0
            playback["started_at_ms"] = now_ms()
            playback["status"] = "loading"
            playback["iteration"] += 1
            playback.pop("pause_reason", None)
            message = next((item for item in self.messages if item["id"] == playback["message_id"]), None)
            if message:
                message["status"] = "presenting"
        elif action == "speed" and rate is not None:
            if rate not in {0.5, 0.75, 1.0, 1.25}:
                raise ValueError("Unsupported playback speed")
            playback["elapsed_ms"] = self.elapsed()
            playback["rate"] = rate
            playback["started_at_ms"] = now_ms()
        elif action in {"complete", "stop"}:
            playback["elapsed_ms"] = playback["total_ms"] if action == "complete" else self.elapsed()
            playback["status"] = "completed" if action == "complete" else "stopped"
            message = next((item for item in self.messages if item["id"] == playback["message_id"]), None)
            if message:
                message["status"] = playback["status"]
            if action == "stop":
                for queued in self.pending:
                    queued["status"] = "cancelled"
                self.pending.clear()
            elif self.pending:
                self._start_playback(self.pending.pop(0))
        self.changed()

    def confirm(self, message_id: str, text: str):
        message = next((message for message in self.messages if message["id"] == message_id and message["role"] == "patient"), None)
        if message is None:
            message = next((word for turn in self.messages for word in turn.get("words", []) if word["id"] == message_id), None)
        if message is None or not text.strip() or len(text) > 500:
            raise ValueError("Không tìm thấy kết quả cần xác nhận.")
        message["text"] = text.strip()
        message["status"] = "confirmed"
        message["uncertain"] = False
        if self.conversation["mode"] == "auto" and self.playback and (self.playback["status"] == "playing" or self.playback.get("pause_reason") == "patient_activity"):
            self.playback.update(elapsed_ms=self.elapsed(), status="paused", pause_reason="patient_reply")
        for turn in self.messages:
            if message in turn.get("words", []):
                from .patient_turns import paraphrase
                turn["raw_text"] = " · ".join(item["text"] for item in turn["words"])
                turn["reading"] = paraphrase(turn["words"])
                turn["text"] = turn["raw_text"] if turn["status"] == "streaming" else turn["reading"]["text"]
                turn["uncertain"] = any(item.get("uncertain") for item in turn["words"])
        self.changed()

    def feedback(self, value: str):
        if value not in {"understood", "repeat"}:
            raise ValueError("Unknown feedback")
        self.turns.finish(now_ms(), "patient_feedback")
        self.messages.append({"id": identity(), "role": "patient", "text": "Tôi đã hiểu" if value == "understood" else "Vui lòng giải thích lại",
                              "created_at_ms": now_ms(), "status": "confirmed", "manual": True})
        self.messages = self.messages[-100:]
        self.changed()
