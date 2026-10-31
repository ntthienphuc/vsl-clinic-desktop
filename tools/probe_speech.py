"""Pace public Vietnamese WAV samples through the real dictation WebSocket."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import time
import sys

import numpy as np
from faster_whisper.audio import decode_audio
from websockets.asyncio.client import connect


ROOT = Path(__file__).resolve().parents[1]


async def probe(args):
    records = []
    for filename in ["6.wav", "91.wav", "test1.wav"]:
        path = ROOT / "research/speech-samples" / filename
        audio = decode_audio(str(path), sampling_rate=16000)
        pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
        uri = args.url.replace("http://", "ws://") + "/ws/speech?token=" + args.token
        connected = time.perf_counter()
        async with connect(uri, max_size=2**20) as socket:
            while True:
                event = json.loads(await socket.recv())
                if event["type"] == "error":
                    raise RuntimeError(event["message"])
                if event["type"] == "ready":
                    break
            ready_ms = (time.perf_counter() - connected) * 1000
            start = time.perf_counter()
            events = []

            async def receive():
                async for payload in socket:
                    event = json.loads(payload)
                    event["received_ms"] = (time.perf_counter() - start) * 1000
                    events.append(event)
                    if event["type"] == "error":
                        raise RuntimeError(event["message"])
                    if event["type"] == "finished":
                        break

            reader = asyncio.create_task(receive())
            data = pcm + bytes(32000)
            for offset in range(0, len(data), 3200):
                await asyncio.sleep(max(0, start + offset / 32000 - time.perf_counter()))
                await socket.send(data[offset:offset + 3200])
            await socket.send(json.dumps({"action": "finish"}))
            await asyncio.wait_for(reader, timeout=30)
            transcripts = [event for event in events if event["type"] == "transcript"]
            record = {"file": filename, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "audio_ms": len(audio) / 16, "ready_ms": ready_ms, "events": transcripts}
            records.append(record)
            print(json.dumps(record, ensure_ascii=False), flush=True)
    outputs = [event for record in records for event in record["events"]]
    report = {"schema": "clinic-speech-probe-v1", "source": "https://github.com/dangnguyenngochai/demo_vietasr/tree/main/demo_wav",
              "note": "Public speech samples for latency smoke checks, not a medical or speaker accuracy benchmark. Audio excluded from shipped app.",
              "records": records, "summary": {}}
    for name, values in {
        "decode_ms": [item["decode_ms"] for item in outputs],
        "queue_ms": [item["queue_ms"] for item in outputs],
        "endpoint_to_text_ms": [item["decode_ms"] + item["queue_ms"] + item["endpoint_audio_ms"] for item in outputs],
    }.items():
        report["summary"][name] = {"count": len(values), "median": float(np.median(values)), "p95": float(np.percentile(values, 95)), "max": max(values)} if values else None
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8768")
    parser.add_argument("--token", default="clinic-test-session")
    parser.add_argument("--output", default=str(ROOT / "docs/evidence/speech-runtime.json"))
    asyncio.run(probe(parser.parse_args()))
