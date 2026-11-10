"""Strict R3 frozen encoder + independently trained target heads. No training."""
import ast
import copy
import hashlib
import importlib.util
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from safetensors.torch import load_file

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "server/vendor"
sys.path.insert(0, str(VENDOR))
sys.path.insert(0, str(VENDOR / "auto_avsr"))
from model import MultiModalFusionClassifier


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(b)
    return h.hexdigest()


class Engine:
    def __init__(self, device=None, overlap_encoders=True):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        torch.set_num_threads(2)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        self.manifest = json.loads((ROOT / "models/MODEL_MANIFEST.json").read_text("utf8"))
        for record in self.manifest["files"]:
            assert sha(ROOT / record["path"]) == record["sha256"], record["path"]
        self.labels = json.loads((ROOT / "models/classes.json").read_text("utf8"))
        assert len(self.labels) == 100
        assert [x["class_id"] for x in self.labels] == [f"W{i:03d}" for i in range(1, 101)]
        assets = ROOT / "models/assets"
        spec = importlib.util.spec_from_file_location("sign_transforms", assets / "sign_transforms.py")
        self.transforms = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = self.transforms
        spec.loader.exec_module(self.transforms)
        source = assets / "spoter_modelling.py"
        nodes = [n for n in ast.parse(source.read_text("utf8")).body
                 if isinstance(n, ast.ClassDef) and n.name in ("SPOTER", "SPOTERTransformerDecoderLayer")]
        scope = dict(torch=torch, nn=torch.nn, copy=copy, Optional=Optional)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), scope)
        path = self.foundation("spoter.safetensors")
        weights = {k.removeprefix("model."): v for k, v in load_file(str(path)).items()}
        self.sign = scope["SPOTER"](weights["linear_class.weight"].shape[0], 108)
        self.sign.load_state_dict(weights, strict=True)
        self.sign.eval().requires_grad_(False)  # exact reference executes sign on CPU
        self.sign_output = []
        self.sign.linear_class.register_forward_pre_hook(lambda m, x: self.sign_output.append(x[0].detach()))
        from espnet.nets.pytorch_backend.e2e_asr_conformer import E2E
        state = torch.load(self.foundation("vlr_pretrained.pt"), map_location="cpu", weights_only=True, mmap=True)
        model = E2E(state["ctc.ctc_lo.weight"].shape[0], "video", ctc_weight=.1)
        model.load_state_dict(state, strict=True)
        del state
        # The research forward never calls decoder/CTC; keep only the strictly
        # loaded encoder graph on GPU. Removing unused modules changes no values.
        self.frontend = model.frontend.eval().requires_grad_(False).to(self.device)
        self.proj = model.proj_encoder.eval().requires_grad_(False).to(self.device)
        self.lip = model.encoder.eval().requires_grad_(False).to(self.device)
        del model
        self.heads = {}
        for mode, rec in self.manifest["heads"].items():
            path = ROOT / rec["checkpoint"]
            assert sha(path) == rec["sha256"]
            ck = torch.load(path, map_location="cpu", weights_only=True)
            assert ck["args"]["seed"] == 17 and ck["args"]["num_classes"] == 100
            fusion = ck["args"]["arm"] if mode == "fusion" else "cross_attention"
            head = MultiModalFusionClassifier(108, 768, 100, fusion=fusion, init_seed=17)
            head.load_state_dict(ck["model"], strict=True)
            self.heads[mode] = head.eval().requires_grad_(False).to(self.device)
        self.manifest_hash = sha(ROOT / "models/MODEL_MANIFEST.json")
        # CPU SPOTER and CUDA mouth inference have independent model state.
        # A single request remains protected by the API's gpu_lock.
        self.encoder_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vsl-mouth") if overlap_encoders and self.device.startswith("cuda") else None

    def close(self):
        if self.encoder_executor is not None:
            self.encoder_executor.shutdown(wait=True)
            self.encoder_executor = None

    def foundation(self, name):
        item = self.manifest["foundations"][name]
        assert sha(item["path"]) == item["sha256"], name
        return Path(item["path"])

    def synchronize(self):
        if self.device.startswith("cuda"):
            torch.cuda.synchronize()

    @torch.inference_mode()
    def _sign_features(self, pose):
        start = time.perf_counter()
        if len(pose) > 70:
            pose = pose[np.linspace(0, len(pose)-1, 70).round().astype(int)]
        x = self.transforms.make_spoter_input(pose, 70)
        self.sign_output.clear()
        self.sign(x[None])
        result = self.sign_output[0].reshape(1, 108).numpy()
        return result, (time.perf_counter()-start)*1000

    @torch.inference_mode()
    def _mouth_features(self, mouth):
        self.synchronize()
        start = time.perf_counter()
        assert mouth.dtype == np.uint8 and mouth.shape[1:] == (96, 96)
        x = torch.from_numpy(mouth[:, 4:92, 4:92].copy()).float().to(self.device)
        x = ((x / 255 - .421) / .165)[None, :, None]
        result = self.lip(self.proj(self.frontend(x)), None)[0][0].float().cpu().numpy()
        self.synchronize()
        return result, (time.perf_counter()-start)*1000

    @torch.inference_mode()
    def features(self, pose=None, mouth=None):
        started = time.perf_counter()
        timing = {}
        s = l = None
        overlap = pose is not None and mouth is not None and self.encoder_executor is not None
        if overlap:
            pending = self.encoder_executor.submit(self._mouth_features, mouth)
            try:
                s, timing["sign_encoder_ms"] = self._sign_features(pose)
            except BaseException:
                # Drain CUDA work before the API releases exclusive ownership.
                pending.result()
                raise
            l, timing["mouth_encoder_ms"] = pending.result()
        else:
            if pose is not None:
                s, timing["sign_encoder_ms"] = self._sign_features(pose)
            if mouth is not None:
                l, timing["mouth_encoder_ms"] = self._mouth_features(mouth)
        timing["encoder_wall_ms"] = (time.perf_counter()-started)*1000
        timing["encoder_schedule"] = "cpu_sign_cuda_mouth_overlap" if overlap else "serial_single_or_cpu"
        return s, l, timing

    @torch.inference_mode()
    def predict(self, sign, mouth, mode):
        if mode not in self.heads:
            raise ValueError("Unknown mode")
        # Never call a masked fusion a unimodal baseline.
        if mode == "sign_only":
            mouth = None
        if mode == "mouth_only":
            sign = None
        if sign is None and mouth is None:
            return {"status": "unavailable", "reason": "no_valid_modality", "mode": mode}
        if mode == "fusion" and (sign is None or mouth is None):
            return {"status": "unavailable", "reason": "fusion_requires_both", "mode": mode}
        s = np.zeros((1, 108), np.float32) if sign is None else sign
        l = np.zeros((1, 768), np.float32) if mouth is None else mouth
        if len(l) > 96:
            l = l[np.linspace(0, len(l)-1, 96).round().astype(int)]
        s, l = [torch.from_numpy(a).float().to(self.device)[None] for a in (s, l)]
        s = torch.nn.functional.layer_norm(s, (108,))
        l = torch.nn.functional.layer_norm(l, (768,))
        sm = torch.full(s.shape[:2], sign is not None, dtype=torch.bool, device=self.device)
        lm = torch.full(l.shape[:2], mouth is not None, dtype=torch.bool, device=self.device)
        start = time.perf_counter()
        logits = self.heads[mode](s, sm, l, lm)[0].float().cpu()
        scores, indices = logits.softmax(-1).topk(5)
        return dict(status="ok", mode=mode, head_ms=(time.perf_counter()-start)*1000,
                    logits=logits.tolist(), top_k=[
                        dict(index=int(i), class_id=self.labels[int(i)]["class_id"],
                             gloss=self.labels[int(i)]["gloss"], score=float(p))
                        for p, i in zip(scores, indices)])
