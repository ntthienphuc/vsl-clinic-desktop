"""Packaged model on four existing VSL100-derived synthetic visibility fixtures."""
import json
import os
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.multimodal_provider import MultimodalProvider
from multimodal.runtime import sha256
VERSION=json.loads((ROOT/"package.json").read_text("utf8"))["version"]
RES=ROOT.parent/"App"/VERSION/"win-unpacked/resources"
QA=ROOT.parent/"Organization/MultimodalIntegration_2026-11-09"
OUT=QA/("visibility-"+VERSION.replace(".",""))


def main():
    OUT.mkdir(exist_ok=False)
    os.environ["PATH"]=os.environ["SystemRoot"]+r"\System32"
    command=[str(RES/"multimodal-runtime/python.exe"),"-B","-u","-X","utf8",
             str(RES/"multimodal/worker.py"),"--assets",str(RES/"assets/multimodal100")]
    events=[]
    provider=MultimodalProvider(RES/"assets",events.append,command=command)
    report=dict(scope="Four previously created VSL100 W068 pixel occlusion/static-rest fixtures, actual packaged worker. No real mask or natural non-sign accuracy.",cases=[])
    try:
        for name in ["no-face","covered-mouth","lower-body-covered","shake-static-rest"]:
            file=QA/"visibility"/(name+".mp4")
            events.clear()
            generation=provider.start(str(file),"video")
            deadline=time.perf_counter()+120
            while time.perf_counter()<deadline:
                if any(e["type"]=="capture" and e.get("generation")==generation and e.get("status") in {"ended","error"} for e in events):
                    break
                time.sleep(.05)
            final=next(e for e in reversed(events) if e["type"]=="capture")
            assert final["status"]=="ended",list(provider.last_errors)
            results=[e for e in events if e["type"] in {"recognition","recognition_unavailable"}]
            row=dict(case=name,source_sha256=sha256(file),final=final,recognition=results,
                     committed=sum(bool(e.get("policy",{}).get("committed")) for e in results))
            report["cases"].append(row)
            print(json.dumps(dict(case=name,committed=row["committed"]),ensure_ascii=True),flush=True)
        report["execution_passed"]=True
        report["no_face_suppresses_speech"]=report["cases"][0]["committed"]==0
        report["static_rest_false_words"]=report["cases"][-1]["committed"]
        report["covered_mouth_committed"]=report["cases"][1]["committed"]
    finally:
        provider.close()
        (OUT/"REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf8")


if __name__=="__main__":
    main()
