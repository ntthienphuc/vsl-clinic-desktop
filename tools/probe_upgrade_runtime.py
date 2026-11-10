"""HTTP concurrency/lifecycle probe against the running packaged desktop engine."""
import argparse
import asyncio
import json
from pathlib import Path
import statistics
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]


async def main(args):
    async with httpx.AsyncClient(base_url=args.url, headers={"Authorization": "Bearer " + args.token}, timeout=40) as client:
        async def post(path, data):
            response = await client.post("/api" + path, json=data)
            response.raise_for_status()
            return response.json()
        async def boot():
            response = await client.get("/api/bootstrap")
            response.raise_for_status()
            return response.json()
        await post("/session/reset", {})
        initial = await boot()
        before = len(initial["state"]["messages"])
        pending = asyncio.create_task(post("/language/suggest", {"text": "Bụng của bạn có bị nhức không"}))
        timings, plans = [], []
        for _ in range(12):
            started = time.perf_counter()
            plans.append(await post("/text/plan", {"text": "Chị có bị đau bụng không? Vui lòng ngồi nghỉ nhé."}))
            timings.append((time.perf_counter() - started) * 1000)
            await asyncio.sleep(.04)
        advice = await pending
        after = await boot()
        unsupported = await client.post("/api/messages", json={"text": "Chị không đau bụng.", "mode": "sign"})
        replay = await post("/messages", {"text": "Chị có bị đau bụng không? Vui lòng ngồi nghỉ nhé.", "mode": "sign"})
        completed = False
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            snapshot = (await boot())["state"]
            if any(item["id"] == replay["id"] and item["status"] == "completed" for item in snapshot["messages"]):
                completed = True
                break
            await asyncio.sleep(.15)
        stale = asyncio.create_task(client.post("/api/language/suggest", json={"text": "Bạn có cảm giác mệt mỏi không"}))
        await asyncio.sleep(.08)
        stopped = await post("/conversation/stop", {})
        stale_result = await stale
        final = await boot()
        report = {
            "version": (await client.get("/healthcheck")).json()["version"],
            "scope": "Actual packaged engine, local model, HTTP concurrent planning and actual patient-renderer completion; no live human speech/sign validation.",
            "language": initial["language"], "speech": initial["speech"],
            "plan_during_model_ms": {"median": statistics.median(timings), "max": max(timings)},
            "advice": advice,
            "checks": {
                "language_bundled": initial["language"]["available"], "speech_bundled": initial["speech"]["available"],
                "400_labels": initial["model"]["labels"] == 400,
                "plans_supported": all(item["supported"] and len(item["clauses"]) == 2 for item in plans),
                "planning_not_blocked_by_model": max(timings) < 1000,
                "local_model_returns_expected_phrase": bool(advice["suggestions"]) and advice["suggestions"][0]["phrase_id"] == "ask-abdomen",
                "suggestion_never_sent": len(after["state"]["messages"]) == before,
                "unsupported_send_blocked": unsupported.status_code == 422,
                "patient_render_completed": completed,
                "old_suggestion_rejected_after_stop": stale_result.status_code == 409,
                "model_released": not final["language"]["loaded"],
                "session_cleared": not stopped["messages"] and not stopped["speech_drafts"] and stopped["playback"] is None,
            },
        }
        output = ROOT / "docs/evidence/upgrade-040-packaged-runtime.json"
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"checks": report["checks"], "concurrent_plan_ms": report["plan_during_model_ms"]}, ensure_ascii=False, indent=2))
        assert all(report["checks"].values()), "Inspect packaged runtime evidence"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--token", required=True)
    asyncio.run(main(parser.parse_args()))
