"""Probe CUDA in a disposable child; CPU inference never loads NVIDIA DLLs."""
import json
from pathlib import Path
import subprocess


def select_runtime(gpu: Path, cpu: Path, env: dict) -> tuple[Path, dict]:
    if env.get('CLINIC_COMPUTE') == 'cpu':
        return cpu, dict(policy='isolated-cuda-probe-v1', selected='cpu', reason='installer_cpu_choice')
    if 'CUDA_VISIBLE_DEVICES' in env and env['CUDA_VISIBLE_DEVICES'].strip() in {'-1', ''}:
        return cpu, dict(policy='isolated-cuda-probe-v1', selected='cpu', reason='cuda_hidden')
    code = """import json,torch
available=torch.cuda.is_available()
if available:
 x=torch.ones((8,8),device='cuda'); (x@x).sum().item(); torch.cuda.synchronize()
print(json.dumps(dict(cuda=available,gpu=torch.cuda.get_device_name() if available else None)))
"""
    try:
        result = subprocess.run([str(gpu / 'python.exe'), '-B', '-c', code],
                                env=env, capture_output=True, text=True, timeout=30,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        info = json.loads(result.stdout) if result.returncode == 0 else {}
        if info.get('cuda'):
            return gpu, dict(policy='isolated-cuda-probe-v1', selected='cuda', reason='cuda_probe_passed', gpu=info['gpu'])
        reason = 'cuda_unavailable' if result.returncode == 0 else 'cuda_probe_exit'
        detail = dict(exit_code=result.returncode)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        reason, detail = 'cuda_probe_failed', dict(error=type(error).__name__)
    return cpu, dict(policy='isolated-cuda-probe-v1', selected='cpu', reason=reason, **detail)
