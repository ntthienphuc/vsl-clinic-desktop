"""Run both real UI/API routes; compare actual inference to a separate manifest."""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "demo/HAI_KICH_BAN_2026-10-31"


async def probe(args):
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "scope": "Actual paced video detector/model and browser avatar; no human microphone or webcam claim.", "scenarios": [], "checks": {}}
    async with httpx.AsyncClient(base_url=args.url, headers={"Authorization": "Bearer " + args.token}, timeout=40) as client:
        async def state():
            r = await client.get("/api/diagnostics")
            r.raise_for_status()
            return r.json()

        async def post(path, data):
            r = await client.post("/api" + path, json=data)
            r.raise_for_status()
            return r.json()

        async def finished(message_id, timeout=40):
            start = time.monotonic()
            while time.monotonic() - start < timeout:
                d = await state()
                message = next(m for m in d["state"]["messages"] if m["id"] == message_id)
                if message["status"] == "completed":
                    return d
                await asyncio.sleep(.12)
            raise TimeoutError("Avatar did not complete " + message_id)

        boot = (await client.get("/api/bootstrap")).json()
        assert boot["state"]["clients"]["patient"] > 0, "Open the real patient UI"
        report["inventory"] = {"avatar_words": len(boot["vocabulary"]), "phrases": len(boot["phrases"]), "recognizer_classes": boot["model"]["labels"], "model_sha256": boot["model"]["sha256"]}
        for scenario in manifest["scenarios"]:
            await post("/session/reset", {})
            result = {"id": scenario["id"], "steps": []}
            for index, step in enumerate(scenario["steps"], 1):
                plan = await post("/text/plan", {"text": step["doctor"]})
                assert plan["supported"] and plan["projection"] == step["doctor_projection"]
                started = time.time() * 1000
                message = await post("/messages", {"text": step["doctor"], "mode": "sign"})
                done = await finished(message["id"])
                playback = done["state"]["playback"]
                paints = [e for e in done["metrics"] if e.get("event") == "patient_avatar_first_frame" and e.get("playback_id") == playback["id"]]
                render = [e for e in done["metrics"] if e.get("event") == "patient_avatar_render_summary" and e.get("playback_id") == playback["id"]]
                record = {"step": index, "doctor": step["doctor"], "projection": plan["projection"], "avatar_completed": True,
                          "avatar_first_frame_ms": paints[0]["painted_at_ms"] - started if paints else None,
                          "video": step["replay"], "expected": step["patient_labels"]}
                record["render"] = render
                old = {w["id"] for m in done["state"]["messages"] for w in m.get("words", [m])}
                path = KIT / step["replay"]["file"]
                with path.open("rb") as f:
                    r = await client.post("/api/capture/upload", files={"file": (path.name, f, "video/mp4")})
                r.raise_for_status()
                generation = r.json()["generation"]
                words, turns = {}, {}
                started = time.monotonic()
                while time.monotonic() - started < 40:
                    d = await state()
                    s = d["state"]
                    if s["capture"].get("generation") == generation:
                        for turn in s["messages"]:
                            new = [w for w in turn.get("words", []) if w["id"] not in old]
                            if new:
                                turns[turn["id"]] = turn
                            for w in new:
                                words.setdefault(w["id"], {"text": w["text"], "score": w.get("confidence"),
                                                          "first_seen_turn_status": turn["status"], "metrics": w.get("metrics")})
                        if s["capture"]["status"] == "error":
                            raise RuntimeError(s["capture"])
                        if s["capture"]["status"] == "ended" and s["patient_turn"] is None:
                            break
                    await asyncio.sleep(.08)
                record["recognized"] = list(words.values())
                record["turns"] = [{"raw": t["raw_text"], "text": t["text"], "status": t["status"]} for t in turns.values()]
                record["checks"] = {"exact_order_no_extras": [w["text"] for w in words.values()] == step["patient_labels"],
                                    "streamed_before_end": len(words) > 0 and all(w["first_seen_turn_status"] == "streaming" for w in words.values()),
                                    "single_finished_turn": len(turns) == 1 and all(t["status"] != "streaming" for t in turns.values()),
                                    "avatar_painted": bool(paints)}
                result["steps"].append(record)
                print(json.dumps({"scenario": scenario["id"], "step": index, "actual": [w["text"] for w in words.values()], "checks": record["checks"]}, ensure_ascii=False), flush=True)
            report["scenarios"].append(result)
        blocked = []
        for text in ["Y tá không đo nhiệt độ.", "Uống thuốc hai viên.", "Bạn cảm thấy thế nào?", "Y tá ơi, hôm nay kiểm tra thân nhiệt giúp em nhé"]:
            before = (await state())["state"]
            r = await client.post("/api/messages", json={"text": text, "mode": "sign"})
            after = (await state())["state"]
            blocked.append({"text": text, "status": r.status_code, "no_message_added": len(before["messages"]) == len(after["messages"]),
                            "no_playback_changed": before["playback"]["id"] == after["playback"]["id"]})
        report["blocked"] = blocked
        report["checks"]["all_ten_turns"] = all(all(r["checks"].values()) for s in report["scenarios"] for r in s["steps"])
        report["checks"]["unknown_meaning_blocked"] = all(r["status"] == 422 and r["no_message_added"] and r["no_playback_changed"] for r in blocked)
        await post("/capture/stop", {})
    output = ROOT / args.output
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["checks"]), flush=True)
    assert all(report["checks"].values()), str(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:58889")
    parser.add_argument("--token", default="ui-smoke")
    parser.add_argument("--output", default="docs/evidence/rehearsal-source-2026-10-31.json")
    asyncio.run(probe(parser.parse_args()))
