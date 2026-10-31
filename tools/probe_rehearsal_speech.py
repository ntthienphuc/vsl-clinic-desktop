"""Synthetic Vietnamese voice -> live ASR -> routing -> actual avatar smoke test."""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request
import numpy as np
import httpx
from faster_whisper.audio import decode_audio
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]


async def main(args):
    catalog = json.loads((ROOT / "demo/scenarios-v0.3.4.json").read_text(encoding="utf-8"))
    cases = [s["doctor"] for scenario in catalog["scenarios"] for s in scenario["steps"]]
    cases.append("Bạn cảm thấy thế nào?")
    folder = ROOT / "research/speech-samples/rehearsal-034"
    folder.mkdir(exist_ok=True)
    provenance, rows = [], []
    for index, phrase in enumerate(cases):
        path = folder / (hashlib.sha256(phrase.encode("utf-8")).hexdigest()[:12] + ".mp3")
        url = "https://translate.google.com/translate_tts?" + urllib.parse.urlencode({"ie": "UTF-8", "client": "tw-ob", "tl": "vi", "q": phrase})
        if not path.exists():
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
                if "audio" not in response.headers.get("Content-Type", ""):
                    raise RuntimeError("Expected TTS audio")
                path.write_bytes(response.read(2 * 1024 * 1024))
        provenance.append({"text": phrase, "file": path.name, "url": url, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (folder / "provenance.json").write_text(json.dumps({"type": "synthetic public test phrases; no microphone or patient data", "records": provenance}, ensure_ascii=False, indent=2), encoding="utf-8")
    async with httpx.AsyncClient(base_url=args.url, headers={"Authorization": "Bearer " + args.token}, timeout=45) as client:
        async def post(path, data):
            r = await client.post("/api" + path, json=data)
            r.raise_for_status()
            return r.json()
        async def state():
            return (await client.get("/api/diagnostics")).json()["state"]
        await post("/session/reset", {})
        await post("/conversation/configure", {"mode": "auto", "source": {"kind": "demo", "demo_id": "395"}})
        await post("/conversation/start", {})
        for index, phrase in enumerate(cases):
            if args.only and index + 1 not in args.only:
                continue
            before = await state()
            old = {m["id"] for m in before["messages"] if m["role"] == "doctor"}
            old_drafts = {d["id"] for d in before["speech_drafts"]}
            audio = decode_audio(str(folder / provenance[index]["file"]), sampling_rate=16000)
            pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
            events = []
            async with connect(args.url.replace("http://", "ws://") + "/ws/speech?live=true&token=" + args.token) as socket:
                while True:
                    event = json.loads(await asyncio.wait_for(socket.recv(), 60))
                    if event["type"] == "error":
                        raise RuntimeError(event)
                    if event["type"] == "ready":
                        break
                started = time.monotonic()
                async def receive():
                    async for payload in socket:
                        event = json.loads(payload)
                        events.append(event)
                        if event["type"] == "finished":
                            return
                        if event["type"] == "error":
                            raise RuntimeError(event)
                reader = asyncio.create_task(receive())
                # Six seconds of silence after one sentence: no ghost transcripts allowed.
                data = bytes(16000) + pcm + bytes(32000 * 6)
                for offset in range(0, len(data), 3200):
                    await asyncio.sleep(max(0, started + offset / 32000 - time.monotonic()))
                    await socket.send(data[offset:offset + 3200])
                await socket.send(json.dumps({"action": "finish"}))
                await asyncio.wait_for(reader, 45)
            current = await state()
            sent = [m for m in current["messages"] if m["role"] == "doctor" and m["id"] not in old]
            drafts = [d for d in current["speech_drafts"] if d["id"] not in old_drafts]
            transcripts = [e for e in events if e["type"] == "transcript"]
            expected_supported = index < len(cases) - 1
            expected_plan = await post("/text/plan", {"text": phrase})
            row = {"input": phrase, "synthetic": True, "transcripts": transcripts,
                   "messages": sent, "drafts": drafts,
                   "checks": {"one_transcript": len(transcripts) == 1,
                              "dispatch": len(sent) == (1 if expected_supported else 0) and len(drafts) == (0 if expected_supported else 1),
                              "same_glosses": not expected_supported or (len(sent) == 1 and [g["id"] for g in sent[0]["glosses"]] == [g["id"] for g in expected_plan["glosses"]])}}
            if sent:
                start = time.monotonic()
                while time.monotonic() - start < 35:
                    current = await state()
                    if next(m for m in current["messages"] if m["id"] == sent[0]["id"])["status"] == "completed":
                        break
                    await asyncio.sleep(.15)
                row["checks"]["avatar_completed"] = next(m for m in current["messages"] if m["id"] == sent[0]["id"])["status"] == "completed"
            rows.append(row)
            print(json.dumps({"input": phrase, "heard": [t.get("text") for t in transcripts], "checks": row["checks"]}, ensure_ascii=False), flush=True)
        await post("/conversation/stop", {})
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "scope": "Synthetic TTS through real paced live WebSocket. Does not validate the user's voice/microphone/room acoustics.", "rows": rows, "passed": all(all(r["checks"].values()) for r in rows)}
    (ROOT / args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    assert report["passed"], "Inspect speech evidence; do not claim unsupported phrases worked"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:58889")
    p.add_argument("--token", default="ui-smoke")
    p.add_argument("--output", default="docs/evidence/rehearsal-speech-2026-10-31.json")
    p.add_argument("--only", type=int, nargs="+")
    asyncio.run(main(p.parse_args()))
