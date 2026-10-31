"""Exercise shared playback state against a real patient renderer."""
import argparse
import asyncio
import json
from pathlib import Path
import time
import httpx

ROOT = Path(__file__).resolve().parents[1]


async def main(args):
    async with httpx.AsyncClient(base_url=args.url, headers={"Authorization": "Bearer " + args.token}, timeout=30) as c:
        async def post(path, payload):
            r = await c.post("/api" + path, json=payload)
            r.raise_for_status()
            return r.json()
        async def state():
            return (await c.get("/api/diagnostics")).json()["state"]
        async def until(predicate):
            start = time.monotonic()
            while time.monotonic() - start < 40:
                s = await state()
                if predicate(s):
                    return s
                await asyncio.sleep(.10)
            raise TimeoutError("Playback control timed out")
        await post("/session/reset", {})
        text = "Bác sĩ khám bệnh. Bạn có đau bụng không? Uống nước."
        m = await post("/messages", {"text": text, "mode": "sign"})
        s = await until(lambda s: s["playback"]["status"] == "playing")
        p = s["playback"]
        paused = await post("/playback", {"action": "pause", "playback_id": p["id"]})
        await asyncio.sleep(.35)
        held = await state()
        checks = {"pause_holds_clock": held["playback"]["status"] == "paused" and held["playback"]["elapsed_ms"] == paused["playback"]["elapsed_ms"]}
        slow = await post("/playback", {"action": "speed", "rate": .75, "playback_id": p["id"]})
        checks["speed_retains_pause"] = slow["playback"]["rate"] == .75 and slow["playback"]["status"] == "paused"
        await post("/playback", {"action": "resume", "playback_id": p["id"]})
        done = await until(lambda s: s["playback"]["status"] == "completed")
        checks["all_clauses_completed"] = len(done["playback"]["clauses"]) == 3 and len(done["playback"]["glosses"]) == 6
        replay = await post("/playback", {"action": "replay", "playback_id": p["id"]})
        checks["replay_new_iteration"] = replay["playback"]["iteration"] == p["iteration"] + 1
        await until(lambda s: s["playback"]["status"] == "playing")
        queued = await post("/messages", {"text": "Cảm ơn.", "mode": "sign"})
        checks["next_message_queued"] = queued["status"] == "queued"
        await post("/playback", {"action": "stop", "playback_id": p["id"]})
        final = await state()
        checks["stop_cancels_queue"] = final["pending_count"] == 0 and next(x for x in final["messages"] if x["id"] == queued["id"])["status"] == "cancelled"
        r = await c.get("/api/diagnostics")
        report = {"checks": checks, "messages": final["messages"], "metrics": r.json()["metrics"]}
        (ROOT / args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(checks))
        assert all(checks.values())


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:58891")
    p.add_argument("--token", default="ui-smoke")
    p.add_argument("--output", default="docs/evidence/playback-controls-2026-10-31.json")
    asyncio.run(main(p.parse_args()))
