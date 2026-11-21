"""Three frozen mouth-pixel fixtures using the actual filtered shipping runtime."""
import argparse
import json
from pathlib import Path
import sys
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--resources', type=Path, required=True)
parser.add_argument('--plan', type=Path, required=True)
parser.add_argument('--mode', choices=['cpu', 'auto'], required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise FileExistsError(args.output)
sys.path.insert(0, str(args.resources.resolve()))
import numpy as np
import torch
from multimodal.runtime import load_contract, sha256

factory, deployment = load_contract(args.resources / 'assets/multimodal100')
started = time.perf_counter()
engine = factory(device='cpu' if args.mode == 'cpu' else None)
rows = []
try:
    engine.warmup()
    load_ms = (time.perf_counter() - started) * 1000
    plan = json.loads(args.plan.read_text('utf8'))
    for clip in plan['clips']:
        assert sha256(clip['pixel_path']) == clip['pixel_sha256']
        with np.load(clip['pixel_path'], allow_pickle=False) as pixels:
            start = time.perf_counter()
            sign, mouth, timing = engine.features(pixels['keypoints'], pixels['mouth'])
            result = engine.predict(sign, mouth, 'fusion')
            rows.append(dict(clip_id=clip['clip_id'], wall_ms=(time.perf_counter()-start)*1000,
                             pixel_sha256=clip['pixel_sha256'], **result))
    report = dict(passed=True, executable=sys.executable, torch=torch.__version__, torch_module=torch.__file__,
                  mode=args.mode, selected_device=engine.device, load_warmup_ms=load_ms,
                  model_manifest_sha256=engine.manifest_hash, rows=rows,
                  scope='3 reused VSL100 fixtures containing real mouth pixels; runtime packaging smoke, no new accuracy benchmark.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf8')
    print(json.dumps({k:v for k,v in report.items() if k != 'rows'}), flush=True)
finally:
    engine.close()
