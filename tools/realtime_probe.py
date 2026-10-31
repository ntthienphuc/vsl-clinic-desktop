"""Exercise real paced video and optionally concurrent avatar playback via the public API."""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import platform
import time

import httpx
import numpy as np
from websockets.asyncio.client import connect


ROOT = Path(__file__).resolve().parents[1]


def distribution(values):
    array = np.asarray([value for value in values if value is not None], dtype=float)
    if not len(array):
        return None
    return {"count": len(array), "median": float(np.median(array)), "p95": float(np.percentile(array, 95)), "max": float(array.max())}


async def probe(args):
    headers = {"Authorization": "Bearer " + args.token}
    records = []
    started = time.time()
    async with httpx.AsyncClient(base_url=args.url, headers=headers, timeout=20) as client:
        bootstrap = (await client.get("/api/bootstrap")).json()
        words = [word for word in bootstrap["vocabulary"] if word.get("model_id") is not None and word.get("demo")]
        if args.ids:
            words = [word for word in words if word["id"] in args.ids.split(",")]
        if args.avatar and bootstrap["state"]["clients"]["patient"] < 1:
            raise RuntimeError("Open the actual patient UI before measuring avatar playback.")
        for word in words:
            websocket_url = args.url.replace("http://", "ws://") + "/ws?role=doctor&token=" + args.token
            async with connect(websocket_url, max_size=2**22) as socket:
                initial = json.loads(await socket.recv())["state"]
                old_ids = {word["id"] for message in initial["messages"] for word in message.get("words", [message])}
                before = time.perf_counter()
                response = await client.post("/api/capture/start", json={"kind": "demo", "demo_id": word["id"]})
                response.raise_for_status()
                generation = response.json()["generation"]
                sent_epoch = None
                message_id = None
                if args.avatar:
                    sent_epoch = time.time() * 1000
                    response = await client.post("/api/messages", json={"text": word["label"], "mode": "sign"})
                    response.raise_for_status()
                    message_id = response.json()["id"]
                observations = []
                results = {}
                playback_id = None
                final = None
                while time.perf_counter() - before < 35:
                    state = json.loads(await asyncio.wait_for(socket.recv(), timeout=20))["state"]
                    received = time.time() * 1000
                    capture = state["capture"]
                    if capture.get("generation") != generation:
                        continue
                    observations.append(dict(capture))
                    for message in [word for turn in state["messages"] for word in turn.get("words", [turn])]:
                        if message["role"] == "patient" and not message.get("manual") and message["id"] not in old_ids:
                            results.setdefault(message["id"], {**message, "probe_received_epoch_ms": received})
                    playback = state["playback"]
                    if playback and playback["message_id"] == message_id:
                        playback_id = playback["id"]
                    avatar_done = not args.avatar or (playback and playback["message_id"] == message_id and playback["status"] in {"completed", "stopped"})
                    if capture["status"] == "error" or (capture["status"] == "ended" and avatar_done):
                        final = state
                        break
                if final is None:
                    raise TimeoutError("Video/avatar did not finish: " + word["label"])
                await asyncio.sleep(0.15)
                diagnostics = (await client.get("/api/diagnostics")).json()
                paint_events = {item.get("message_id"): item for item in diagnostics["metrics"] if item.get("event") == "doctor_result_painted"}
                for identity, result in results.items():
                    metric = result["metrics"]
                    end_epoch = metric.get("last_active_epoch_ms")
                    result["end_to_server_ms"] = metric["server_result_epoch_ms"] - end_epoch if end_epoch else None
                    result["server_to_ws_ms"] = result["probe_received_epoch_ms"] - metric["server_result_epoch_ms"]
                    paint = paint_events.get(identity)
                    result["end_to_doctor_paint_ms"] = paint["painted_at_ms"] - end_epoch if paint and end_epoch else None
                    result["matches_demo_label"] = result["text"].casefold() == word["label"].casefold()
                avatar_paint = next((item for item in diagnostics["metrics"] if item.get("event") == "patient_avatar_first_frame" and item.get("playback_id") == playback_id), None)
                record = {
                    "word": word["label"], "id": word["id"], "generation": generation,
                    "elapsed_seconds": time.perf_counter() - before,
                    "capture_final": final["capture"], "capture_observations": observations,
                    "recognitions": list(results.values()),
                    "avatar_send_to_first_frame_ms": avatar_paint["painted_at_ms"] - sent_epoch if avatar_paint and sent_epoch else None,
                }
                records.append(record)
                text = ", ".join(item["text"] for item in results.values()) or "(no segment)"
                print(f"{word['label']}: {text}; processed={final['capture'].get('processed')}; dropped={final['capture'].get('dropped')}; avatar_ms={record['avatar_send_to_first_frame_ms']}", flush=True)
        await client.post("/api/capture/stop", json={})
    recognitions = [item for record in records for item in record["recognitions"]]
    observations = [item for record in records for item in record["capture_observations"]]
    report = {
        "schema": "clinic-runtime-probe-v1", "started_epoch": started,
        "environment": {"platform": platform.platform(), "processor": platform.processor()},
        "model": bootstrap["model"], "duplex_avatar": args.avatar,
        "note": "Paced recordings, not webcam accuracy. Gesture end uses the last frame classified active by the segmenter, not human annotation. Browser paint means rAF/render completion, not display-photon latency.",
        "summary": {
            "videos": len(records), "outputs": len(recognitions),
            "videos_with_output": sum(bool(item["recognitions"]) for item in records),
            "videos_with_matching_top1": sum(any(item["matches_demo_label"] for item in record["recognitions"]) for record in records),
            "end_to_server_ms": distribution([item["end_to_server_ms"] for item in recognitions]),
            "end_to_doctor_paint_ms": distribution([item["end_to_doctor_paint_ms"] for item in recognitions]),
            "server_to_ws_ms": distribution([item["server_to_ws_ms"] for item in recognitions]),
            "inference_ms": distribution([item["metrics"]["inference_ms"] for item in recognitions]),
            "queue_ms": distribution([item["metrics"]["queue_ms"] for item in recognitions]),
            "frame_age_ms": distribution([item.get("frame_age_ms") for item in observations if item["status"] not in {"starting", "ended"}]),
            "detector_ms": distribution([item.get("detect_ms") for item in observations if item["status"] not in {"starting", "ended"}]),
            "avatar_send_to_first_frame_ms": distribution([item["avatar_send_to_first_frame_ms"] for item in records]),
            "capture_errors": [item["capture_final"] for item in records if item["capture_final"]["status"] == "error"],
        },
        "records": records,
    }
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    parser.add_argument("--token", default="local-development")
    parser.add_argument("--ids", default="")
    parser.add_argument("--avatar", action="store_true")
    parser.add_argument("--output", default=str(ROOT / "research/runtime-realtime.json"))
    asyncio.run(probe(parser.parse_args()))
