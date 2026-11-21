"""Resolve the original frozen implementation from a self-contained asset root."""
from pathlib import Path
import hashlib
import json
import sys


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(chunk)
    return h.hexdigest()


def load_contract(root):
    root = Path(root).resolve(strict=True)
    deployment = json.loads((root / "DEPLOYMENT.json").read_text("utf8"))
    for rec in deployment["files"]:
        path = (root / rec["path"]).resolve(strict=True)
        if not path.is_relative_to(root) or sha256(path) != rec["sha256"]:
            raise ValueError("Multimodal asset integrity check failed: " + rec["path"])
    sys.path.insert(0, str(root))
    if deployment.get("profile") == "slgcn-autoavsr":
        from .engine_r3 import R3Engine
        from .auto_device import AutoDeviceEngine

        def autoavsr(device=None, quantized=None):
            if quantized is not None:
                raise ValueError('Cannot override release weights')
            return AutoDeviceEngine(lambda **opt: R3Engine(root, **opt),
                                    deployment['inference']['cpu_precision'] == 'ffn-int8', device=device)
        return autoavsr, deployment
    if deployment.get("profile") == "slgcn-avhubert":
        from .engine_r3 import R3Engine
        inference = deployment.get('inference', {})
        if inference.get('device') == 'auto':
            from .auto_device import AutoDeviceEngine
            quantized = (root / inference['quantized_encoder']).resolve(strict=True)
            declared = {row['path'] for row in deployment['files']}
            if not quantized.is_relative_to(root) or quantized.relative_to(root).as_posix() not in declared:
                raise ValueError('Automatic CPU fallback manifest is not declared')

            class PackagedAutoEngine(AutoDeviceEngine):
                def __init__(self, device=None, quantized=None, **kwargs):
                    if quantized is not None or kwargs:
                        raise ValueError('Cannot override automatic deployment weights')
                    super().__init__(lambda **options: R3Engine(root, **options),
                                     root / inference['quantized_encoder'], device=device)

            return PackagedAutoEngine, deployment

        class PackagedR3Engine(R3Engine):
            def __init__(self, **kwargs):
                # A separately packaged CPU experiment owns its precision choice.
                # The regular deployment has no override and keeps GPU/CPU auto.
                inference = deployment.get('inference', {})
                if inference:
                    if inference.get('device') != 'cpu':
                        raise ValueError('Unsupported packaged inference profile')
                    quantized = (root / inference['quantized_encoder']).resolve(strict=True)
                    declared = {row['path'] for row in deployment['files']}
                    if not quantized.is_relative_to(root) or quantized.relative_to(root).as_posix() not in declared:
                        raise ValueError('Packaged quantized manifest is not declared')
                    if kwargs.get('device') not in (None, 'cpu') or kwargs.get('quantized'):
                        raise ValueError('Cannot override a packaged CPU experiment')
                    kwargs.update(device='cpu', quantized=quantized)
                super().__init__(root, **kwargs)

        return PackagedR3Engine, deployment
    from server.engine import Engine

    class PackagedEngine(Engine):
        def foundation(self, name):
            path = (root / deployment["foundations"][name]).resolve(strict=True)
            if not path.is_relative_to(root):
                raise ValueError("Foundation outside asset root")
            # Already hashed above; still enforce the original model manifest.
            if sha256(path) != self.manifest["foundations"][name]["sha256"]:
                raise ValueError("Foundation hash mismatch")
            return path

    return PackagedEngine, deployment
