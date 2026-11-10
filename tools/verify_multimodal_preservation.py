"""Recheck audited original research inputs and preserved baseline launch files."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/"Organization/MultimodalIntegration_2026-11-09"


def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda:stream.read(8*1024**2),b""):h.update(data)
    return h.hexdigest()


def main():
    audit=json.loads((OUT/"AUDIT_SOURCE_AND_LABELS.json").read_text("utf8"))
    rows={}
    def visit(value):
        if isinstance(value,dict):
            if value.get("path") and value.get("sha256") and value.get("exists"):
                rows[value["path"]]=value["sha256"]
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(audit["source_files"])
    visit(audit["dependencies"])
    source=[dict(path=name,sha256=checksum,unchanged=digest(Path(name))==checksum) for name,checksum in rows.items()]
    baseline=json.loads((OUT/"baseline/fingerprints.json").read_text("utf8"))
    baseline=[dict(path=row["path"],sha256=row["sha256"],unchanged=digest(Path(row["path"]))==row["sha256"])
              for row in baseline if Path(row["path"]).is_absolute()]
    report=dict(original_research_files=source,baseline_launch_files=baseline,
        baseline_snapshot_sha256=digest(OUT/"baseline/source_before.zip"),
        passed=all(row["unchanged"] for row in source+baseline))
    (OUT/"PRESERVATION_FINAL.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf8")
    assert report["passed"]
    print(json.dumps(dict(research_files=len(source),baseline_files=len(baseline),passed=report["passed"])))


if __name__=="__main__":main()
