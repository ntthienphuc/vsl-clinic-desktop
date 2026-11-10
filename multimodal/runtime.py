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
    if deployment.get("profile") == "slgcn-avhubert":
        from .engine_r3 import R3Engine

        class PackagedR3Engine(R3Engine):
            def __init__(self, **kwargs):
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
