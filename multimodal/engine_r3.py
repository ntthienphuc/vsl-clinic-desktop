"""Strict frozen SL-GCN + AV-HuBERT, VSL100 R3 cross-attention head.

Both encoders execute serially on the selected device; a capture worker owns
one segment at a time. No recording or network access is performed here.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

from .runtime import sha256
from .avhubert_loader import load as load_avhubert


class R3Engine:
    def __init__(self, root, device=None, **_):
        self.root = Path(root)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        torch.set_num_threads(2)
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        self.manifest = json.loads((self.root/"models/MODEL_MANIFEST.json").read_text("utf8"))
        self.manifest_hash = sha256(self.root/"models/MODEL_MANIFEST.json")
        self.labels = json.loads((self.root/"models/classes.json").read_text("utf8"))
        assert sha256(self.root/"models/classes.json") == self.manifest["label_sha256"]
        assert [v["class_id"] for v in self.labels] == [f"W{i:03d}" for i in range(1,101)]
        r3 = self.root/"r3"
        sys.path[:0] = [str(r3/"deps"), str(r3/"code"), str(self.root/"server/vendor")]
        from sign_backbones import build
        from model import MultiModalFusionClassifier
        self.prepare_sign, self.forward_sign, self.sign_info = build(r3, "slgcn", self.device)
        self.mouth_model, self.forward_mouth, self.mouth_info = load_avhubert(
            r3/"vendor/avhubert_source", r3/"assets/avhubert",
            r3/"avhubert_preset.json", self.device)
        rec = self.manifest["heads"]["fusion"]
        checkpoint = self.root/rec["checkpoint"]
        assert sha256(checkpoint) == rec["sha256"]
        ck = torch.load(checkpoint, map_location="cpu", weights_only=True)
        args = ck["args"]
        assert (args["seed"],args["sign_dim"],args["lip_dim"],args["num_classes"],args["arm"]) == (
            17,256,1024,100,"cross_attention")
        assert Path(args["fold"]).name == "r3_loso_01.json"
        head = MultiModalFusionClassifier(256,1024,100,fusion="cross_attention",init_seed=17)
        head.load_state_dict(ck["model"], strict=True)
        self.head = head.eval().requires_grad_(False).to(self.device)

    def close(self):
        self.synchronize()

    def synchronize(self):
        if self.device.startswith("cuda"):
            torch.cuda.synchronize()

    @torch.inference_mode()
    def _sign_features(self, pose):
        start = time.perf_counter()
        if len(pose) > 150:
            pose = pose[np.linspace(0,len(pose)-1,150).round().astype(int)]
        feature = self.forward_sign(self.prepare_sign(pose)[None])[0]
        self.synchronize()
        return feature, (time.perf_counter()-start)*1000

    @torch.inference_mode()
    def _mouth_features(self, mouth):
        start = time.perf_counter()
        feature = self.forward_mouth(mouth)
        self.synchronize()
        return feature, (time.perf_counter()-start)*1000

    @torch.inference_mode()
    def features(self, pose=None, mouth=None):
        start = time.perf_counter()
        timing = {}
        s = l = None
        if pose is not None:
            s,timing["sign_encoder_ms"] = self._sign_features(pose)
        if mouth is not None:
            l,timing["mouth_encoder_ms"] = self._mouth_features(mouth)
        timing["encoder_wall_ms"] = (time.perf_counter()-start)*1000
        timing["encoder_schedule"] = "serial_slgcn_avhubert_" + self.device
        return s,l,timing

    @torch.inference_mode()
    def predict(self, sign, mouth, mode):
        if mode != "fusion":
            raise ValueError("This deployment contains the genuine fusion head only")
        if sign is None or mouth is None:
            return dict(status="unavailable", reason="fusion_requires_both", mode=mode)
        assert sign.shape == (1,256) and mouth.ndim == 2 and mouth.shape[1] == 1024
        assert np.isfinite(sign).all() and np.isfinite(mouth).all()
        if len(mouth) > 96:
            mouth = mouth[np.linspace(0,len(mouth)-1,96).round().astype(int)]
        s,l = [torch.from_numpy(a).float().to(self.device)[None] for a in (sign,mouth)]
        s = torch.nn.functional.layer_norm(s,(256,))
        l = torch.nn.functional.layer_norm(l,(1024,))
        sm = torch.ones(s.shape[:2],dtype=torch.bool,device=self.device)
        lm = torch.ones(l.shape[:2],dtype=torch.bool,device=self.device)
        started = time.perf_counter()
        logits = self.head(s,sm,l,lm)[0].float().cpu()
        scores,indices = logits.softmax(-1).topk(5)
        return dict(status="ok",mode=mode,head_ms=(time.perf_counter()-started)*1000,
            logits=logits.tolist(),top_k=[
                dict(index=int(i),class_id=self.labels[int(i)]["class_id"],
                     gloss=self.labels[int(i)]["gloss"],score=float(p)) for p,i in zip(scores,indices)])

    def warmup(self):
        # Warmup never emits a recognition event or touches a camera.
        pose = np.ones((70,75,4),np.float32)
        positions = np.linspace(.1,.9,75,dtype=np.float32)
        for axis in range(3):
            pose[:,:,axis] = np.roll(positions,axis*17)
        sign,lip,_ = self.features(pose,np.full((70,96,96),128,np.uint8))
        self.predict(sign,lip,"fusion")
        self.synchronize()
