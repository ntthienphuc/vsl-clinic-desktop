"""One offline payload: actual CUDA probe, INT8 CPU fallback, bounded retry."""
from __future__ import annotations

import gc

import torch


def cuda_failure(error: Exception) -> bool:
    message = str(error).casefold()
    return isinstance(error, (RuntimeError, OSError)) and any(term in message for term in (
        "cuda", "cudnn", "cublas", "nvidia", "out of memory", "no kernel image", "driver"))


class AutoDeviceEngine:
    def __init__(self, factory, quantized, device=None):
        if device not in (None, "cpu", "cuda"):
            raise ValueError("Unsupported inference device")
        self._factory = factory
        self._quantized = quantized
        self._allow_fallback = device is None
        self._engine = None
        self.runtime_selection = dict(policy="cuda-probe-or-cpu-int8-v1", requested=device or "auto",
                                      fallback=False, reason="cpu_requested" if device == "cpu" else "cuda_unavailable")
        chosen = "cpu"
        if device != "cpu":
            try:
                if torch.cuda.is_available():
                    # Availability alone cannot establish that kernels can run
                    # on this driver/architecture. Exercise allocation + GEMM.
                    probe = torch.ones((8, 8), device="cuda")
                    (probe @ probe).sum().item()
                    torch.cuda.synchronize()
                    del probe
                    self.runtime_selection.update(gpu=torch.cuda.get_device_name(), reason="cuda_probe_passed")
                    chosen = "cuda"
                elif device == "cuda":
                    raise RuntimeError("CUDA is unavailable")
            except (RuntimeError, OSError) as error:
                if device == "cuda":
                    raise
                self.runtime_selection.update(fallback=True, reason="cuda_probe_failed", detail=str(error)[:240])
        failure = None
        try:
            self._engine = factory(device=chosen, quantized=quantized if chosen == "cpu" else None)
        except (RuntimeError, OSError) as error:
            if chosen != "cuda" or not self._allow_fallback or not cuda_failure(error):
                raise
            failure = str(error)
        if failure is not None:
            self._fallback(failure)
        self.runtime_selection["selected"] = self._engine.device

    def __getattr__(self, name):
        return getattr(self._engine, name)

    def _fallback(self, reason):
        # Leave the CUDA traceback before collecting the old tensors. Never
        # retry an invalid input, altered model artifact or a failing CPU path.
        self._engine = None
        gc.collect()
        try:
            torch.cuda.empty_cache()
        except (RuntimeError, OSError):
            pass
        self._engine = self._factory(device="cpu", quantized=self._quantized)
        self.runtime_selection.update(fallback=True, reason="cuda_execution_failed", detail=reason[:240], selected="cpu")

    def _invoke(self, method, *args):
        failure = None
        try:
            return getattr(self._engine, method)(*args)
        except (RuntimeError, OSError) as error:
            if self._engine.device != "cuda" or not self._allow_fallback or not cuda_failure(error):
                raise
            failure = str(error)
        self._fallback(failure)
        return getattr(self._engine, method)(*args)

    def warmup(self):
        return self._invoke("warmup")

    def features(self, pose=None, mouth=None):
        return self._invoke("features", pose, mouth)

    def predict(self, sign, mouth, mode):
        return self._invoke("predict", sign, mouth, mode)

    def synchronize(self):
        return self._invoke("synchronize")

    def close(self):
        if self._engine is not None:
            self._engine.close()
