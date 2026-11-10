"""Patient recognition choices, distinct dictionaries and one capture owner."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import threading

MODES = ("fusion", "sign_only")


def load_catalogs(assets: Path):
    samples = json.loads((assets / "multimodal-samples/manifest.json").read_text("utf8"))["entries"]
    sample_by_id = {s["class_id"]: s for s in samples}
    mapping = json.loads((assets / "multimodal100/label_mapping.json").read_text("utf8"))
    fusion = [dict(id=m["canonical_concept_id"], label=m["display_text"], model_id=None,
                   class_id=m["class_id"], voice_key=m["voice_key"],
                   category="Sức khỏe" if 64 <= m["class_index"] <= 81 else "Giao tiếp",
                   demo=sample_by_id.get(m["class_id"], {}).get("demo")) for m in mapping]
    catalog = json.loads((assets / "catalog.json").read_text("utf8"))["words"]
    categories = {w["model_id"]: w["category"] for w in catalog}
    with (assets / "gloss.csv").open(encoding="utf8", newline="") as f:
        labels = list(csv.reader(f))
    sign = [dict(id=f"sign400:{i}", label=text, model_id=int(i), voice_key=i,
                 category=categories.get(int(i), "Từ khác"),
                 demo=f"/assets/samples/{int(i):03d}.mp4" if (assets / f"samples/{int(i):03d}.mp4").is_file() else None)
            for i, text in labels]
    assert len(fusion) == 100 and len(sign) == 400
    return {"fusion": fusion, "sign_only": sign}


class RecognitionModes:
    """Keep loaded providers warm; never let two providers own the camera."""

    def __init__(self, assets, publish, factories=None):
        self.assets = Path(assets)
        self.publish = publish
        self.mode = "fusion"
        self.generation = 0
        self.providers = {}
        self.factories = factories
        self.running = False
        self.switching = False
        self.last_source = None
        self.lock = threading.RLock()

    def _event(self, mode, event):
        if not self.running or mode != self.mode or event.get("generation") != self.generation:
            return
        if mode == "sign_only" and event.get("type") == "recognition":
            event = dict(event, engine_family="legacy400", actual_mode="sign_only",
                         contract="clinic-slgcn400-onnx-v1")
        self.publish(event)

    def _provider(self, mode):
        if mode not in self.providers:
            callback = lambda e: self._event(mode, e)
            if self.factories:
                provider = self.factories[mode](callback)
            elif mode == "fusion":
                from .multimodal_provider import MultimodalProvider
                provider = MultimodalProvider(self.assets, callback)
            else:
                from .capture import CaptureEngine
                from .recognition import Recognizer
                provider = CaptureEngine(Recognizer(self.assets), callback)
            self.providers[mode] = provider
        return self.providers[mode]

    def warmup(self):
        provider = self._provider(self.mode)
        if hasattr(provider, "warmup"):
            provider.warmup()

    def activate(self, mode):
        if mode not in MODES:
            raise ValueError("Chọn Ký hiệu + khẩu hình hoặc Chỉ ký hiệu.")
        with self.lock:
            if mode == self.mode:
                return
            self.switching = True
            try:
                self.stop()
                provider = self._provider(mode)
                if hasattr(provider, "warmup"):
                    provider.warmup()
                self.mode = mode
            finally:
                self.switching = False

    def start(self, source, source_kind):
        with self.lock:
            self.stop()
            self.generation += 1
            provider = self._provider(self.mode)
            provider.generation = self.generation - 1
            self.running = True
            self.last_source = (source, source_kind)
            try:
                assert provider.start(source, source_kind) == self.generation
            except Exception:
                self.running = False
                raise
            return self.generation

    def stop(self):
        with self.lock:
            self.running = False
            provider = self.providers.get(self.mode)
            if provider:
                getattr(provider, "stop_and_wait", provider.stop)()

    def close(self):
        with self.lock:
            self.running = False
            for provider in self.providers.values():
                getattr(provider, "close", provider.stop)()

    def preview_frame(self):
        provider = self.providers.get(self.mode)
        version, data = provider.preview_frame() if provider and self.running else (0, None)
        return (self.generation, version), data

    def info(self):
        provider = self.providers.get(self.mode)
        if self.mode == "fusion":
            result = provider.info() if provider else dict(name="Ký hiệu + khẩu hình", labels=100,
                family="multimodal100", sha256=None, capture_profile="clinic-mm100-ram-r3-v1")
            status = result.get("worker", {}).get("status", "loading")
        else:
            from .recognition import CAPTURE_PROFILE
            result = dict(name="Chỉ ký hiệu", labels=400, family="legacy400",
                sha256=provider.recognizer.sha256 if provider else None, capture_profile=CAPTURE_PROFILE)
            status = "ready" if provider else "loading"
        return dict(result, mode=self.mode, status=status, switching=self.switching)
