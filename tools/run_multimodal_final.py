"""Sequential targeted checks; do not overlap model runs or change checkpoints."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/"Organization/MultimodalIntegration_2026-11-09"


def main():
    for name in ["stress/LIFECYCLE.json","capture/RESULTS.json","capture/SUMMARY.json","visibility/RESULTS.json","cpu/REPORT.json"]:
        file=OUT/name
        if file.exists():shutil.copy2(file,file.with_stem(file.stem+"-before-final"))
    phases=[("long-packaged",["tools/probe_multimodal_lifecycle.py","--packaged"]),
            ("capture-final",["tools/probe_multimodal_capture.py"]),
            ("visibility-final",["tools/probe_multimodal_visibility.py"]),
            ("cpu-final",["tools/probe_multimodal_cpu.py"])]
    completed=[]
    for name,args in phases:
        (OUT/"FINAL_CHECK_PROGRESS.json").write_text(json.dumps(dict(phase=name,completed=completed,status="running")),"utf8")
        started=time.perf_counter()
        with (OUT/(name+".log")).open("w",encoding="utf8") as log:
            result=subprocess.run([sys.executable,"-X","utf8",*args],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        completed.append(dict(phase=name,exit_code=result.returncode,elapsed_seconds=time.perf_counter()-started))
        if result.returncode:
            (OUT/"FINAL_CHECK_PROGRESS.json").write_text(json.dumps(dict(completed=completed,status="failed")),"utf8")
            raise SystemExit(result.returncode)
    (OUT/"FINAL_CHECK_PROGRESS.json").write_text(json.dumps(dict(completed=completed,status="complete"),indent=2),"utf8")
    print(json.dumps(completed),flush=True)


if __name__=="__main__":main()
