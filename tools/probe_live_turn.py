"""Paced composite of real isolated clips: transport/turn test, not sentence accuracy."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import time

import cv2
import httpx
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]


def make_video():
    destination = ROOT / "research/live-turn-379-204.mp4"
    writer = cv2.VideoWriter(str(destination), cv2.VideoWriter_fourcc(*"mp4v"), 30, (640, 480))
    sources = []
    count = 0
    last = None
    for identity in (379, 204):
        source = ROOT / f"assets/samples/{identity:03d}.mp4"
        capture = cv2.VideoCapture(str(source))
        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = []
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frames.append(cv2.resize(frame, (640, 480)))
        capture.release()
        for index in range(round(len(frames) * 30 / fps)):
            last = frames[min(len(frames) - 1, round(index * fps / 30))]
            writer.write(last)
            count += 1
        sources.append({"model_id": identity, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "ends_at_ms": count / 30 * 1000})
        if identity == 379:
            # Explicit 0.8 s hold: the unchanged isolated recognizer needs a
            # visible word boundary. Back-to-back arbitrary clips can merge.
            for _ in range(24):
                writer.write(last)
                count += 1
    for _ in range(75):
        writer.write(last)
    writer.release()
    return destination, sources


async def probe(args):
    path, sources = make_video()
    headers = {"Authorization": "Bearer " + args.token}
    async with httpx.AsyncClient(base_url=args.url, headers=headers, timeout=30) as client:
        response = await client.post("/api/session/reset")
        response.raise_for_status()
        async with connect(args.url.replace("http://", "ws://") + "/ws?role=doctor&token=" + args.token) as socket:
            await socket.recv()
            start = time.time() * 1000
            with path.open("rb") as handle:
                response = await client.post("/api/capture/upload", files={"file": (path.name, handle, "video/mp4")})
            response.raise_for_status()
            generation = response.json()["generation"]
            words = {}
            turns = {}
            stream_snapshots = []
            while time.time() * 1000 - start < 20000:
                state = json.loads(await asyncio.wait_for(socket.recv(), 10))["state"]
                if state["capture"].get("generation") != generation:
                    continue
                for turn in state["messages"]:
                    if turn.get("kind") != "patient_turn":
                        continue
                    turns[turn["id"]] = turn
                    for word in turn["words"]:
                        if word["id"] not in words:
                            words[word["id"]] = {"text": word["text"], "turn_id": turn["id"], "received_ms": time.time() * 1000 - start,
                                                  "turn_status_when_received": turn["status"], "metrics": word["metrics"]}
                            stream_snapshots.append({"elapsed_ms": time.time() * 1000 - start, "live_text": turn["text"], "status": turn["status"]})
                            print(json.dumps(stream_snapshots[-1], ensure_ascii=False), flush=True)
                if state["capture"]["status"] == "error":
                    raise RuntimeError(state["capture"])
                if state["capture"]["status"] == "ended" and state["patient_turn"] is None:
                    break
            diagnostics = (await client.get("/api/diagnostics")).json()
            paint = {item.get("message_id"): item for item in diagnostics["metrics"] if item.get("event") == "doctor_result_painted"}
            for identity, word in words.items():
                word["paint"] = paint.get(identity)
            report = {"schema": "clinic-live-turn-probe-v1", "note": "Concatenated heldout isolated recordings with 800 ms hold between words and a frozen final frame. Tests streaming and turn grouping, not natural continuous sentence recognition.",
                      "sources": sources, "words": list(words.values()), "turns": list(turns.values()), "stream_snapshots": stream_snapshots,
                      "checks": {"correct_order": [word["text"] for word in words.values()] == ["Đau", "Mệt"],
                                 "single_turn": len(turns) == 1,
                                 "immediate_streaming_words": len(words) == 2 and all(word["turn_status_when_received"] == "streaming" for word in words.values()),
                                 "finished": bool(turns) and all(turn["status"] != "streaming" for turn in turns.values())}}
            destination = ROOT / args.output
            destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report["checks"]), flush=True)
            assert all(report["checks"].values()), f"Inspect {destination}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8773")
    parser.add_argument("--token", default="local-development")
    parser.add_argument("--output", default="docs/evidence/live-turn-v0.3.json")
    asyncio.run(probe(parser.parse_args()))
