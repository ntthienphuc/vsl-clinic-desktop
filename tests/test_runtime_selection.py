"""A missing/broken GPU must select a process that never loads CUDA Torch."""
from pathlib import Path
from types import SimpleNamespace
import subprocess

import pytest

from backend.runtime_selection import select_runtime


GPU, CPU = Path('gpu'), Path('cpu')


def test_installer_cpu_choice_does_not_probe_gpu(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError('A CPU installation must never invoke the excluded GPU runtime')
    monkeypatch.setattr(subprocess, 'run', fail)
    runtime, info = select_runtime(GPU, CPU, {'CLINIC_COMPUTE': 'cpu'})
    assert runtime == CPU and info['reason'] == 'installer_cpu_choice'


def test_hidden_cuda_never_imports_gpu_torch(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError('Masked GPU must not load NVIDIA libraries')
    monkeypatch.setattr(subprocess, 'run', fail)
    runtime, info = select_runtime(GPU, CPU, {'CUDA_VISIBLE_DEVICES': '-1'})
    assert runtime == CPU and info['reason'] == 'cuda_hidden'


@pytest.mark.parametrize('code,output,expected', [
    (0, '{"cuda":true,"gpu":"Fixture GPU"}', GPU),
    (0, '{"cuda":false,"gpu":null}', CPU),
    (-1073741819, '', CPU),  # Native driver access violation from real Windows log.
    (0, 'invalid protocol', CPU),
])
def test_isolated_probe_exit_selects_runtime(monkeypatch, code, output, expected):
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: SimpleNamespace(returncode=code, stdout=output))
    runtime, info = select_runtime(GPU, CPU, {})
    assert runtime == expected
    assert info['selected'] == ('cuda' if expected == GPU else 'cpu')


def test_probe_timeout_selects_cpu(monkeypatch):
    def timeout(*a, **k):
        raise subprocess.TimeoutExpired('cuda probe', 30)
    monkeypatch.setattr(subprocess, 'run', timeout)
    assert select_runtime(GPU, CPU, {})[0] == CPU


def test_native_gpu_crash_restarts_once_on_cpu_before_capture(monkeypatch):
    import sys
    from backend.multimodal_provider import MultimodalProvider
    from backend import multimodal_provider
    assets = Path(__file__).resolve().parents[1] / 'assets'
    code = """import json,os,sys
if '--device' not in sys.argv: os._exit(17)
print(json.dumps(dict(type='worker_ready',device='cpu')),flush=True)
for line in sys.stdin:
 if json.loads(line)['action']=='shutdown': break
"""
    original = subprocess.Popen
    launches = []
    def launch(command, **kwargs):
        launches.append(command)
        return original([sys.executable, *command[1:]], **kwargs)
    monkeypatch.setattr(subprocess, 'Popen', launch)
    monkeypatch.setattr(multimodal_provider, 'select_runtime', lambda *a: (GPU, dict(selected='cuda')))
    provider = MultimodalProvider(assets, lambda e: None, command=[sys.executable, '-u', '-c', code])
    provider.runtime_options = (GPU, CPU)
    try:
        provider.warmup()
        assert provider.ready.wait(6), provider.info()
        assert provider.worker_info['device'] == 'cpu'
        assert provider.runtime_choice['reason'] == 'gpu_worker_failed'
        assert len(launches) == 2
        assert launches[1][-2:] == ['--device', 'cpu']
    finally:
        provider.close()
    assert provider.process is None


def test_native_failure_during_capture_does_not_replay_old_word(monkeypatch):
    import sys
    import time
    from backend.multimodal_provider import MultimodalProvider
    from backend import multimodal_provider
    code = """import json,os,sys
cpu='--device' in sys.argv
print(json.dumps(dict(type='worker_ready',device='cpu' if cpu else 'cuda')),flush=True)
for line in sys.stdin:
 r=json.loads(line)
 if r['action']=='start':
  if not cpu: os._exit(17)
  print(json.dumps(dict(type='recognition',generation=r['generation'],predictions=[])),flush=True)
 elif r['action']=='shutdown': break
"""
    original = subprocess.Popen
    monkeypatch.setattr(subprocess, 'Popen', lambda command, **kw: original([sys.executable, *command[1:]], **kw))
    monkeypatch.setattr(multimodal_provider, 'select_runtime', lambda *a: (GPU, dict(selected='cuda')))
    events = []
    assets = Path(__file__).resolve().parents[1] / 'assets'
    provider = MultimodalProvider(assets, events.append, command=[sys.executable, '-u', '-c', code])
    provider.runtime_options = (GPU, CPU)
    try:
        first = provider.start('fixture', 'video')
        deadline = time.monotonic() + 5
        while provider.worker_info.get('status') != 'error' and time.monotonic() < deadline:
            time.sleep(.01)
        assert provider.force_cpu
        assert not any(e['type'] == 'recognition' for e in events)
        second = provider.start('fixture', 'video')
        deadline = time.monotonic() + 5
        while not any(e['type'] == 'recognition' for e in events) and time.monotonic() < deadline:
            time.sleep(.01)
        assert [e['generation'] for e in events if e['type'] == 'recognition'] == [second]
        assert second > first and provider.worker_info['device'] == 'cpu'
    finally:
        provider.close()
