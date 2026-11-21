"""Load an explicitly fingerprinted CPU INT8 artifact; never rewrite FP32 weights."""
import hashlib
import json
from pathlib import Path

import torch


def read_manifest(path, original_sha256):
    path = Path(path).resolve(strict=True)
    record = json.loads(path.read_text('utf8'))
    if record['schema'] != 'clinic-avhubert-transformer-int8-v1' or record['source_sha256'] != original_sha256:
        raise ValueError('Quantized encoder provenance mismatch')
    artifact = (path.parent/record['file']).resolve(strict=True)
    if not artifact.is_relative_to(path.parent):
        raise ValueError('Quantized encoder outside its manifest folder')
    with artifact.open('rb') as stream:
        actual = hashlib.file_digest(stream,'sha256').hexdigest()
    if actual != record['sha256']:
        raise ValueError('Quantized encoder checksum mismatch')
    return record, artifact


def install_linear_skeleton(model):
    # No float weight conversion at startup. Packed INT8 tensors are loaded
    # from the measured artifact. The remaining float tensors load by assign.
    from torch.ao.nn.quantized.dynamic import Linear
    names = []
    for layer in model.encoder.layers:
        layer.self_attn.onnx_trace = True
    for name,module in list(model.named_modules()):
        if name.startswith('encoder.layers.') and name.rsplit('.',1)[-1] in {'fc1','fc2','q_proj','k_proj','v_proj','out_proj'} and isinstance(module,torch.nn.Linear):
            parent_name, child = name.rsplit('.',1)
            parent = model.get_submodule(parent_name)
            setattr(parent,child,Linear(module.in_features,module.out_features,bias_=module.bias is not None,dtype=torch.qint8))
            names.append(name)
    if len(names) != 144:
        raise ValueError('Unexpected AV-HuBERT quantized layer count')
    return names
