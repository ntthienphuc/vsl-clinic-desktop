"""Verify direct INT8 artifact loading in the separate CPU-only runtime."""
import json
from pathlib import Path
import sys
import time
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from multimodal.runtime import load_contract,sha256
from tools.probe_cpu_quantization import memory

out=ROOT.parent/'Organization/VoicePreviewCPU_2026-11-10'
manifest=out/'cpu-transformer-int8/QUANTIZED_ENCODER.json'
expected=json.loads((manifest.parent/'REPORT.json').read_text('utf8'))
plan=json.loads((ROOT.parent/'Organization/MultimodalIntegration_2026-11-09/fusion_explore/PLAN.json').read_text('utf8'))
assert torch.version.cuda is None and not torch.cuda.is_available()
cls,_=load_contract(ROOT/'assets/multimodal100')
start=time.perf_counter()
engine=cls(device='cpu',quantized=manifest)
engine.warmup()
rows=[]
for clip,reference in zip(plan['clips'],expected['clips']):
    assert sha256(clip['pixel_path'])==clip['pixel_sha256']
    with np.load(clip['pixel_path'],allow_pickle=False) as pixels:
        started=time.perf_counter()
        sign,mouth,timing=engine.features(pixels['keypoints'],pixels['mouth'])
        prediction=engine.predict(sign,mouth,'fusion')
        elapsed=(time.perf_counter()-started)*1000
    difference=float(np.max(np.abs(np.asarray(prediction['logits'])-reference['logits'])))
    assert difference<1e-5,(clip['clip_id'],difference)
    rows.append(dict(clip_id=clip['clip_id'],logit_delta=difference,top1=prediction['top_k'][0],wall_ms=elapsed,timing=timing))
report=dict(passed=True,torch=torch.__version__,cuda_available=torch.cuda.is_available(),memory=memory(),
            load_and_replay_ms=(time.perf_counter()-start)*1000,rows=rows,
            manifest_sha256=sha256(manifest),scope='Direct serialized INT8 vs conversion-in-memory on same 3 fixed inputs; CPU runtime only.')
(out/'CPU_DIRECT_LOAD.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
print(json.dumps(report,ensure_ascii=True),flush=True)
engine.close()
