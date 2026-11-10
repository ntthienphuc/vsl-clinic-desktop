"""One actual bundled-runtime fixture with CUDA hidden; no CPU speed promise."""
from pathlib import Path
import json
import os
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.multimodal_provider import MultimodalProvider
VERSION=json.loads((ROOT/"package.json").read_text("utf8"))["version"]
OUT=ROOT.parent/("Organization/MultimodalIntegration_2026-11-09/cpu-"+VERSION.replace(".",""))
RES=ROOT.parent/"App"/VERSION/"win-unpacked/resources"


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    os.environ["CUDA_VISIBLE_DEVICES"]="-1"
    os.environ["PATH"]=os.environ["SystemRoot"]+r"\System32"
    command=[str(RES/"multimodal-runtime/python.exe"),"-B","-u","-X","utf8",str(RES/"multimodal/worker.py"),"--assets",str(RES/"assets/multimodal100")]
    events=[]
    p=MultimodalProvider(RES/"assets",events.append,command=command)
    report=dict(scope="One packaged worker/fixture with CUDA_VISIBLE_DEVICES=-1; no clean-machine or sustained CPU realtime claim.")
    started=time.perf_counter()
    try:
        p.start(str(RES/"assets/multimodal-samples/W068.mp4"),"video")
        while time.perf_counter()-started<150:
            if any(e["type"]=="capture" and e.get("status") in {"ended","error"} for e in events):break
            time.sleep(.1)
        assert p.worker_info.get("device")=="cpu",p.worker_info
        assert events[-1].get("status")=="ended",events[-1]
        assert any(e["type"] in {"recognition","recognition_unavailable"} for e in events)
        report["passed"]=True
    except Exception as exc:
        report.update(passed=False,error=repr(exc))
        raise
    finally:
        report.update(worker=p.worker_info,events=events,elapsed_seconds=time.perf_counter()-started,stderr=list(p.last_errors))
        p.close()
        (OUT/"REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf8")
        print(json.dumps(dict(passed=report["passed"],worker=report["worker"])),flush=True)


if __name__=="__main__":main()
