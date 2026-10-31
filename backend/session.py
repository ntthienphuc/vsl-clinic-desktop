"""One authoritative conversation and playback clock shared by both windows."""
from __future__ import annotations

import asyncio
import copy
import time
import uuid

from .text_to_sign import TextPlanner
from .playback import build_timeline
from .patient_turns import PatientTurns


def now_ms():
    return time.time() * 1000


def identity():
    return uuid.uuid4().hex[:12]


class ClinicSession:
    def __init__(self, planner: TextPlanner, durations: dict[str, float], join_profile: dict | None = None):
        self.planner = planner
        self.durations = durations
        self.join_profile = join_profile or {}
        self.listeners = {}
        self.loop = None
        self.revision = 0
        self.metrics = []
        self.reset()

    def reset(self):
        self.session_id = identity()
        self.messages = []
        self.capture = {"status": "idle", "generation": 0}
        self.playback = None
        self.pending = []
        self.current_result = None
        self.turns = PatientTurns()
        self.conversation = {"status": "idle", "mode": "manual", "epoch": identity(),
                             "source": {"kind": "camera", "camera_index": 0}, "started_at_ms": None}
        self.speech_drafts = []
        self.speech_seen = set()
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
            if event["status"] in {"error", "idle", "no_person", "starting"}:
                self.current_result = None
        elif event["type"] == "recognition":
            predictions = event["predictions"]
            last_doctor = next((item for item in reversed(self.messages)
                                if item["role"] == "doctor" and item.get("presented_at_ms")), {})
            recent = now_ms() - last_doctor.get("presented_at_ms", 0) < 60000
            question_id = last_doctor.get("phrase_id")
            if last_doctor.get("mode") == "sign" and self.playback and self.playback["message_id"] == last_doctor.get("id"):
                shown = [clause for clause in self.playback["clauses"] if clause["start_ms"] <= self.elapsed()]
                question_id = shown[-1].get("phrase_id") if shown else None
            context = self.planner.contextual_candidates(predictions, question_id if recent else None)
            top = predictions[0] if predictions else {"gloss": "Chưa nhận rõ", "score": 0}
            message = {
                "id": identity(), "role": "patient", "text": top["gloss"],
                "created_at_ms": now_ms(), "status": "candidate", "confidence": top["score"],
                "uncertain": top["score"] < 0.55 or bool(event.get("quality_warning")), "predictions": predictions,
                "quality_warning": event.get("quality_warning"),
                "context_candidates": context,
                "metrics": {key: value for key, value in event.items() if key not in {"predictions", "type"}},
            }
            turn = self.turns.append(message, now_ms())
            if not any(item["id"] == turn["id"] for item in self.messages):
                self.messages.append(turn)
            self.messages = self.messages[-100:]
            self.current_result = message
            self.metrics.append({"type": "recognition", "message_id": message["id"], **event})
            self.metrics = self.metrics[-500:]
        self.changed()

    def capture_stopped(self, generation):
        self.turns.finish(now_ms(), "capture_stopped")
        self.capture = {"status": "idle", "generation": generation}
        self.current_result = None
        self.changed()

    def tick(self):
        if self.turns.tick(now_ms(), self.capture):
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

    def stop_conversation(self):
        self.conversation.update(status="idle", epoch=identity())
        self.turns.finish(now_ms(), "conversation_stopped")
        if self.playback and self.playback["status"] not in {"stopped", "completed"}:
            self.control_playback("stop", self.playback["id"])
        self.changed()

    def speech_result(self, result: dict, epoch: str):
        if self.conversation["status"] != "active" or self.conversation["epoch"] != epoch:
            return None
        key = result["utterance_id"]
        if key in self.speech_seen or not result["text"].strip():
            return None
        self.speech_seen.add(key)
        try:
            plan = self.planner.plan(result["text"])
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
                message = self.send(result["text"], "sign")
                message["speech_utterance_id"] = key
                return {"status": "sent", "message_id": message["id"]}
            except ValueError as error:
                reason = str(error)
                reason_code = "busy"
        draft = {"id": key, "text": result["text"], "created_at_ms": now_ms(),
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
