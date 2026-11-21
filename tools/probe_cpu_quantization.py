"""Small, fixed VSL100 CPU comparison; original checkpoints are read-only."""
import argparse
import ctypes
import gc
import json
from pathlib import Path
import statistics
import sys
import time

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from multimodal.runtime import load_contract, sha256


def memory():
    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong)] + [
            (name, ctypes.c_size_t) for name in ['PeakWorkingSetSize','WorkingSetSize',
            'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
    record = Counters()
    record.cb = ctypes.sizeof(record)
    get_process = ctypes.windll.kernel32.GetCurrentProcess
    get_process.restype = ctypes.c_void_p
    get_memory = ctypes.windll.psapi.GetProcessMemoryInfo
    get_memory.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    get_memory.restype = ctypes.c_int
    if not get_memory(get_process(), ctypes.byref(record), record.cb):
        raise ctypes.WinError()
    return dict(rss_mib=record.WorkingSetSize/1024**2, peak_rss_mib=record.PeakWorkingSetSize/1024**2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['fp32','attention-eager-fp32','ffn-int8','transformer-int8'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    plan_path = ROOT.parent/'Organization/MultimodalIntegration_2026-11-09/fusion_explore/PLAN.json'
    plan = json.loads(plan_path.read_text('utf8'))
    inputs = []
    for clip in plan['clips']:
        assert sha256(clip['pixel_path']) == clip['pixel_sha256']
        with np.load(clip['pixel_path'], allow_pickle=False) as data:
            inputs.append((clip,data['keypoints'].copy(),data['mouth'].copy()))
    cls, deployment = load_contract(ROOT/'assets/multimodal100')
    engine = cls(device='cpu')
    details = dict(variant=args.variant,torch=torch.__version__,threads=torch.get_num_threads(),
                   cpu_backend=torch.backends.quantized.engine,converted_layers=[])
    if args.variant in {'attention-eager-fp32','transformer-int8'}:
        # The original fairseq eager branch calls projection modules instead of
        # bypassing them through F.multi_head_attention_forward(weight=...).
        for layer in engine.mouth_model.encoder.layers:
            layer.self_attn.onnx_trace = True
    if args.variant in {'ffn-int8','transformer-int8'}:
        # Avoid fairseq attention's direct weight access. Only its two large
        # feed-forward Linear layers per block change precision in this arm.
        from torch.ao.quantization import quantize_dynamic, default_dynamic_qconfig
        selected = {'fc1','fc2'} if args.variant == 'ffn-int8' else {'fc1','fc2','q_proj','k_proj','v_proj','out_proj'}
        names = [name for name,module in engine.mouth_model.named_modules()
                 if name.startswith('encoder.layers.') and name.rsplit('.',1)[-1] in selected
                 and isinstance(module, torch.nn.Linear)]
        assert len(names) == (48 if args.variant == 'ffn-int8' else 144), names
        details['converted_layers'] = names
        details['converted_parameters'] = sum(p.numel() for name,module in engine.mouth_model.named_modules()
                                               if name in names for p in module.parameters())
        quantize_dynamic(engine.mouth_model, {name:default_dynamic_qconfig for name in names},
                         dtype=torch.qint8,inplace=True)
        artifact = args.output/('avhubert-'+args.variant+'.pt')
        torch.save(engine.mouth_model.state_dict(),artifact)
        details.update(artifact=str(artifact),artifact_bytes=artifact.stat().st_size,artifact_sha256=sha256(artifact))
        gc.collect()
    engine.warmup()
    details['memory_after_warmup'] = memory()
    rows = []
    for clip,pose,mouth in inputs:
        trials=[]
        for _ in range(2):
            started=time.perf_counter()
            sign,lip,timing=engine.features(pose,mouth)
            result=engine.predict(sign,lip,'fusion')
            trials.append(dict(**timing,head_ms=result['head_ms'],wall_ms=(time.perf_counter()-started)*1000))
        row=dict(clip_id=clip['clip_id'],pixel_sha256=clip['pixel_sha256'],frames=len(mouth),
                 logits=result['logits'],top_k=result['top_k'],trials=trials,
                 median_ms=statistics.median(t['wall_ms'] for t in trials))
        rows.append(row)
        print(json.dumps({k:v for k,v in row.items() if k not in {'logits','top_k','trials'}},ensure_ascii=True),flush=True)
    report=dict(passed=True,scope='Three pre-existing fixed VSL100 pixel fixtures, two warm repetitions, CPU 2 threads. No training, independent accuracy or live realtime claim.',
                plan_sha256=sha256(plan_path),contract=deployment['contract'],details=details,clips=rows,
                final_memory=memory(),median_ms=statistics.median(r['median_ms'] for r in rows))
    (args.output/'REPORT.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf8')
    print(json.dumps(dict(passed=True,variant=args.variant,median_ms=report['median_ms'],memory=report['final_memory'])),flush=True)
    engine.close()


if __name__ == '__main__':
    main()
