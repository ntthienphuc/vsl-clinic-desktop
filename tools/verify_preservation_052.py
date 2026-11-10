"""Recheck existing preservation receipts; never write original artifacts."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "Organization/ModesPilot_2026-11-10"


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    previous = json.loads((ROOT.parent / "Organization/MultimodalIntegration_2026-11-09/release-051/PRESERVATION.json").read_text("utf8"))
    rows = [dict(path=r["path"], sha256=r["sha256"],
                 unchanged=digest(Path(r["path"])) == r["sha256"]) for r in previous["files"]]
    receipt = OUT / "receipt-051.json"
    current = ROOT.parent / "App/0.5.1/win-unpacked/BUILD_RECEIPT.json"
    checks = dict(original_inputs_unchanged=all(r["unchanged"] for r in rows),
                  previous_receipt_unchanged=digest(current) == digest(receipt))
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(), files=rows, checks=checks,
                  source_snapshot_sha256=digest(OUT / "source-before-052.zip"), passed=all(checks.values()))
    (OUT / "preservation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), "utf8")
    print(json.dumps(dict(files=len(rows), checks=checks, passed=report["passed"])))
    assert report["passed"]


if __name__ == "__main__":
    main()
