"""Run the source engine with a deterministic token for local UI smoke checks."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=58889)
    parser.add_argument("--token", default="ui-smoke")
    args = parser.parse_args()
    os.environ["CLINIC_ASSETS"] = str(ROOT / "assets")
    os.environ["CLINIC_FRONTEND"] = str(ROOT / "dist")
    os.environ["CLINIC_TOKEN"] = args.token
    os.environ["PYTHONUNBUFFERED"] = "1"
    os.environ["PYTHONUTF8"] = "1"
    sys.argv = [str(ROOT / "backend" / "main.py"), "--port", str(args.port)]
    from backend.main import main as engine_main

    engine_main()


if __name__ == "__main__":
    main()
