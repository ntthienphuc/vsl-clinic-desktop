import torch
import logging
from pathlib import Path
from collections import OrderedDict
from safetensors.torch import load_file as load_safetensors
from transformers import PreTrainedModel, FeatureExtractionMixin
from transformers.modeling_outputs import ImageClassifierOutput
from .configuration import SLGCNConfig
from .decouple_gcn_attn import Model


def _resolve_pretrained_path(pretrained: str) -> Path:
    path = Path(str(pretrained))
    if path.is_dir():
        for filename in ("model.safetensors", "pytorch_model.bin"):
            candidate = path / filename
            if candidate.exists():
                return candidate
    return path


def _load_pretrained_state(path: Path) -> dict:
    if path.suffix == ".safetensors":
        return load_safetensors(str(path))
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    if isinstance(checkpoint, dict):
        if "state_dict" in checkpoint:
            return checkpoint["state_dict"]
        if "weights" in checkpoint:
            return checkpoint["weights"]
    return checkpoint


class SLGCNFeatureExtractor(FeatureExtractionMixin):
    def __init__(self, config: SLGCNConfig = SLGCNConfig(), **kwargs) -> None:
        super().__init__(**kwargs)
        self.arch = config.arch
        self.num_frames = config.num_frames
        self.num_points = config.num_points
        self.in_channels = config.in_channels
        self.num_people = config.num_people
        self.window_size = config.window_size
        self.is_vector = config.is_vector
        self.bone_stream = config.bone_stream
        self.motion_stream = config.motion_stream


class SLGCNForGraphClassification(PreTrainedModel):
    config_class = SLGCNConfig

    def __init__(
        self,
        config: SLGCNConfig = SLGCNConfig(),
        label2id: dict = None,
        id2label: dict = None,
    ) -> None:
        super().__init__(config=config)
        self.label2id = label2id if label2id is not None else config.label2id
        self.id2label = id2label if id2label is not None else config.id2label
        self.num_classes = len(self.label2id)

        self.model = Model(
            num_classes=self.num_classes,
            num_points=self.config.num_points,
            num_people=self.config.num_people,
            groups=self.config.groups,
            block_size=self.config.block_size,
            in_channels=self.config.in_channels,
            labeling_mode=self.config.labeling_mode,
        )

        pretrained_path = _resolve_pretrained_path(self.config.pretrained)
        if pretrained_path.exists():
            weights = _load_pretrained_state(pretrained_path)
            if any(k.startswith("model.") for k in weights):
                missing_keys, unexpected_keys = self.load_state_dict(weights, strict=False)
                if missing_keys or unexpected_keys:
                    logging.info(
                        "Loaded SL-GCN local pretrained with "
                        f"missing_keys={len(missing_keys)}, unexpected_keys={len(unexpected_keys)}"
                    )
            else:
                weights = OrderedDict([
                    [k.split('module.')[-1], v.to(self.device)]
                    for k, v in weights.items()
                ])

                if weights["fc.weight"].size(0) != self.num_classes:
                    self.config.ignored_weights.extend(["fc.weight", "fc.bias"])
                for w in self.config.ignored_weights:
                    weights.pop(w, None)

                state = self.model.state_dict()
                diff = list(set(state.keys()).difference(set(weights.keys())))
                logging.warning("Can not load these weights: " + ", ".join(diff))
                state.update(weights)
                self.model.load_state_dict(state)

        for i, param in enumerate(self.model.parameters()):
            if i >= config.num_frozen_layers:
                break
            param.requires_grad = False

    def forward(
        self,
        poses: torch.Tensor,
        labels: torch.Tensor = None,
    ) -> torch.Tensor:
        poses = poses.to(dtype=torch.float32)
        keep_prob = 0.9 if self.training else 1.0
        logits = self.model(poses, keep_prob=keep_prob)
        if labels is not None:
            labels = labels.to(logits.device, dtype=torch.long)
            loss = torch.nn.functional.cross_entropy(logits, labels)
            return ImageClassifierOutput(logits=logits, loss=loss)
        return ImageClassifierOutput(logits=logits)
