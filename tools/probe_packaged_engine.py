"""Smoke probe for the frozen ClinicEngine payload."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def request(base: str, path: str, token: str, method: str = "GET", payload: object | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request_obj = Request(base + path, data=body, headers=headers, method=method)
    with urlopen(request_obj, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_health(base: str, token: str, process: subprocess.Popen) -> dict:
    last_error: Exception | None = None
    for _ in range(120):
        if process.poll() is not None:
            raise RuntimeError(f"ClinicEngine exited before healthcheck: {process.returncode}")
        try:
            return request(base, "/healthcheck", token)
        except (OSError, URLError) as error:
            last_error = error
            time.sleep(0.25)
    raise TimeoutError(f"ClinicEngine healthcheck timed out: {last_error}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, default=ROOT / "release" / "desktop-v0.3.4" / "win-unpacked")
    parser.add_argument("--port", type=int, default=58888)
    args = parser.parse_args()

    package = args.package.resolve()
    engine = package / "resources" / "engine" / "ClinicEngine.exe"
    assets = package / "resources" / "assets"
    frontend = package / "resources" / "frontend"
    if not engine.is_file() or not (assets / "semantic_bank.json").is_file() or not (frontend / "index.html").is_file():
        raise FileNotFoundError("Frozen engine, semantic asset, or frontend payload is missing")

    token = "packaged-smoke"
    env = os.environ.copy()
    env.update({"CLINIC_ASSETS": str(assets), "CLINIC_FRONTEND": str(frontend), "CLINIC_TOKEN": token})
    process = subprocess.Popen([str(engine), "--port", str(args.port)], cwd=str(package / "resources"), env=env)
    base = f"http://127.0.0.1:{args.port}"
    try:
        health = wait_for_health(base, token, process)
        headers = {"Authorization": f"Bearer {token}"}
        bootstrap = request(base, "/api/bootstrap", token)
        plan = request(base, "/api/text/plan", token, "POST", {"text": "Y tá ơi, đo nhiệt độ nha", "mode": "sign"})
        review_plan = request(base, "/api/text/plan", token, "POST", {"text": "Tôi ăn cơm", "mode": "sign"})
        blocked_plan = request(base, "/api/text/plan", token, "POST", {"text": "Y tá ơi, không đo nhiệt độ", "mode": "sign"})
        long_review_plan = request(
            base,
            "/api/text/plan",
            token,
            "POST",
            {"text": "Y tá ơi, hôm nay kiểm tra thân nhiệt giúp em nhé", "mode": "sign"},
        )
        result = {
            "health": health,
            "model": bootstrap["model"],
            "vocabulary_count": len(bootstrap["vocabulary"]),
            "phrase_count": len(bootstrap["phrases"]),
            "semantic_plan": {
                "supported": plan["supported"],
                "projection": plan.get("projection", []),
                "decision": plan.get("semantic", {}).get("decision"),
                "omitted": plan.get("semantic", {}).get("omitted", []),
            },
            "review_guard": {
                "input": "Tôi ăn cơm",
                "supported": review_plan["supported"],
                "decision": review_plan.get("semantic", {}).get("decision"),
                "applied": review_plan.get("semantic", {}).get("applied", False),
            },
            "meaning_guard": {
                "input": "Y tá ơi, không đo nhiệt độ",
                "supported": blocked_plan["supported"],
                "unsupported": [item["text"] for item in blocked_plan.get("unsupported", [])],
            },
            "long_sentence_review": {
                "input": "Y tá ơi, hôm nay kiểm tra thân nhiệt giúp em nhé",
                "supported": long_review_plan["supported"],
                "decision": long_review_plan.get("semantic", {}).get("decision"),
                "candidate_projection": long_review_plan.get("semantic", {}).get("candidate_projection", []),
                "unmatched": [item["text"] for item in long_review_plan.get("semantic", {}).get("unmatched", [])],
                "applied": long_review_plan.get("semantic", {}).get("applied", False),
                "message": long_review_plan.get("message", ""),
            },
            "asset_bytes": (assets / "semantic_bank.json").stat().st_size,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        request(base, "/api/shutdown", token, "POST")
    finally:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait(timeout=8)


if __name__ == "__main__":
    main()
