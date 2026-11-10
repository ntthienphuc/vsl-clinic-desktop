"""Replay frozen VSL100 input pixels through the actual staged Clinic R3 engine."""
import json
import sys
import time
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from multimodal.runtime import load_contract, sha256
QA = ROOT.parent/"Organization/MultimodalIntegration_2026-11-09/fusion_explore"
RESEARCH = Path(r"E:\Paper\MultiModel Paper\VSL100_R3_20261106/results")


def main():
    out = QA/"clinic-r3-parity"
    out.mkdir(exist_ok=False)
    plan = json.loads((QA/"PLAN.json").read_text("utf8"))
    cls,deployment = load_contract(ROOT/"assets/multimodal100")
    engine = cls()
    engine.warmup()
    manifest = engine.manifest
    run = RESEARCH/manifest["heads"]["fusion"]["run_id"]
    references = {}
    for split in ["test","validation"]:
        references.update({r["clip_id"]:r for r in json.loads((run/(split+"_predictions.json")).read_text("utf8"))})
    rows = []
    features = []
    for clip in plan["clips"]:
        assert sha256(clip["pixel_path"]) == clip["pixel_sha256"]
        with np.load(clip["pixel_path"],allow_pickle=False) as data:
            s,l,timing = engine.features(data["keypoints"],data["mouth"])
        features.append((s,l))
        result = engine.predict(s,l,"fusion")
        probs = torch.tensor(result["logits"]).softmax(-1).numpy()
        ref = references[clip["clip_id"]]
        assert ref["source_sha256"] == clip["source_sha256"]
        reference_probs = np.asarray(ref["probabilities"])
        errors = {}
        for name,feature in [("slgcn_replication_fp32",s),("avhubert_replication_fp32",l)]:
            rec = clip["features"][name]
            assert sha256(rec["path"]) == rec["sha256"]
            cached = np.load(rec["path"],allow_pickle=False)
            assert feature.shape == cached.shape
            errors[name] = float(np.abs(feature-cached).max())
            assert np.allclose(feature,cached,atol=2e-4,rtol=2e-4)
        error = float(np.max(np.abs(probs-reference_probs)))
        assert np.allclose(probs,reference_probs,atol=2e-4,rtol=2e-4)
        assert int(probs.argmax()) == int(reference_probs.argmax())
        row = dict(clip_id=clip["clip_id"],feature_max_abs=errors,probabilities_max_abs=error,
                   top1=result["top_k"][0],timing=timing,head_ms=result["head_ms"])
        rows.append(row)
        print(json.dumps(row,ensure_ascii=True),flush=True)
    base = np.asarray(engine.predict(*features[0],"fusion")["logits"])
    changed_sign = np.asarray(engine.predict(features[1][0],features[0][1],"fusion")["logits"])
    changed_mouth = np.asarray(engine.predict(features[0][0],features[1][1],"fusion")["logits"])
    sensitivity = dict(changed_sign_logit_delta=float(np.max(np.abs(base-changed_sign))),
                       changed_mouth_logit_delta=float(np.max(np.abs(base-changed_mouth))))
    assert all(v>1e-3 for v in sensitivity.values())
    assert engine.predict(features[0][0],None,"fusion")["status"] == "unavailable"
    assert engine.predict(None,features[0][1],"fusion")["status"] == "unavailable"
    report = dict(passed=True,contract=deployment["contract"],manifest_sha256=engine.manifest_hash,
                  scope="3 fixed VSL100 video-derived pixel sequences; exact 100-label output vs saved original research predictions; not live accuracy",
                  clips=rows,modality_sensitivity=sensitivity,missing_modality_suppressed=True,
                  peak_cuda_allocated_mib=torch.cuda.max_memory_allocated()/1024**2,
                  peak_cuda_reserved_mib=torch.cuda.max_memory_reserved()/1024**2)
    (out/"REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),"utf8")
    print(json.dumps(report,ensure_ascii=True),flush=True)
    engine.close()


if __name__=="__main__":
    main()
