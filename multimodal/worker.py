"""Private newline-JSON pipe; no HTTP listener and no recording endpoint."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"])
    args = parser.parse_args()
    protocol = sys.stdout
    sys.stdout = sys.stderr  # Third-party print() must not corrupt the protocol.
    lock = threading.Lock()

    def send(event):
        with lock:
            protocol.write(json.dumps(event, ensure_ascii=True, allow_nan=False) + "\n")
            protocol.flush()

    capture, engine = None, None
    try:
        from multimodal.runtime import load_contract
        engine_class, deployment = load_contract(args.assets)
        from multimodal.capture import MultimodalCapture
        started = time.perf_counter()
        engine = engine_class(device=args.device)
        # Pay one-time CUDA/module initialization before a patient's first word.
        # Synthetic constant features never create a capture event or a word.
        import numpy as np
        import torch
        warmed_at = time.perf_counter()
        with torch.inference_mode():
            if hasattr(engine, "warmup"):
                engine.warmup()
            else:
                engine.sign_output.clear()
                engine.sign(torch.zeros((1, 70, 54, 2)))
                engine.sign_output.clear()
                lip, _ = engine._mouth_features(np.full((70, 96, 96), 128, np.uint8))
                engine.predict(np.zeros((1, 108), np.float32), lip, "fusion")
            engine.synchronize()
        warmup_ms = (time.perf_counter() - warmed_at) * 1000
        mapping = json.loads((args.assets / "label_mapping.json").read_text("utf8"))
        capture = MultimodalCapture(engine, args.assets, mapping, send)
        send(dict(type="worker_ready", contract=deployment["contract"], device=engine.device,
                  pid=os.getpid(), load_ms=(time.perf_counter() - started) * 1000,
                  warmup_ms=warmup_ms,
                  manifest_sha256=engine.manifest_hash, storage="ram_only"))
        # EOF from a dead parent is also a shutdown request.
        for line in sys.stdin:
            request = json.loads(line)
            action = request["action"]
            if action == "start":
                capture.start(request["source"], request["source_kind"], int(request["generation"]))
            elif action == "stop":
                capture.stop()
                send(dict(type="worker_stopped", generation=request["generation"]))
            elif action == "shutdown":
                break
            else:
                raise ValueError("unknown_worker_command")
    except Exception as exc:
        send(dict(type="worker_error", error_code=type(exc).__name__ + ": " + str(exc)))
        return 1
    finally:
        if capture is not None:
            capture.stop()
        if engine is not None:
            engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
