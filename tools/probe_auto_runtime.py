"""Bounded comparison of real auto/CPU/fallback models on fixed VSL100 pixels."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from multimodal.runtime import load_contract, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['auto', 'cpu', 'no-cuda', 'fault'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Preserve earlier results; choose another output')
    if args.mode == 'no-cuda':
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    import torch
    factory, deployment = load_contract(ROOT / 'assets/multimodal100')
    began = time.perf_counter()
    engine = factory(device='cpu' if args.mode == 'cpu' else None)
    if args.mode == 'fault':
        assert engine.device == 'cuda'
        def failure():
            raise RuntimeError('CUDA out of memory: deliberate acceptance fault, no real allocation')
        engine._engine.warmup = failure
    engine.warmup()
    load_ms = (time.perf_counter() - began) * 1000
    if args.mode in {'cpu', 'no-cuda', 'fault'}:
        assert engine.device == 'cpu' and engine.mouth_info['precision'] == 'transformer_dynamic_int8'
    plan = json.loads((ROOT.parent / 'Organization/MultimodalIntegration_2026-11-09/fusion_explore/PLAN.json').read_text('utf8'))
    rows = []
    try:
        for clip in plan['clips']:
            assert sha256(clip['pixel_path']) == clip['pixel_sha256']
            with np.load(clip['pixel_path'], allow_pickle=False) as pixels:
                started = time.perf_counter()
                sign, mouth, timing = engine.features(pixels['keypoints'], pixels['mouth'])
                result = engine.predict(sign, mouth, 'fusion')
                rows.append(dict(clip_id=clip['clip_id'], pixel_sha256=clip['pixel_sha256'],
                                 wall_ms=(time.perf_counter()-started)*1000, timing=timing, **result))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report = dict(passed=True, mode=args.mode, torch=torch.__version__, device=engine.device,
                      selection=engine.runtime_selection, mouth_info=engine.mouth_info, load_warmup_ms=load_ms,
                      manifest_sha256=engine.manifest_hash, rows=rows,
                      scope='Fixed VSL100 mouth pixels, bounded model replay. Fault mode injects a CUDA error then runs real CPU inference. No clean-PC claim.')
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), 'utf8')
        print(json.dumps({key:report[key] for key in ['passed','mode','torch','device','selection','load_warmup_ms']}), flush=True)
    finally:
        engine.close()


if __name__ == '__main__':
    main()
