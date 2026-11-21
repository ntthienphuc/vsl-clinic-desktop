"""Visual-only Auto-AVSR encoder, matching the locked R3 VLR inputs."""
import sys

import numpy as np
import torch
from torch import nn


def load_visual(root, device, quantized):
    sys.path.insert(0, str(root / 'server/vendor/auto_avsr'))
    from espnet.nets.pytorch_backend.frontend.resnet import video_resnet
    from espnet.nets.pytorch_backend.encoder.conformer_encoder import ConformerEncoder

    network = nn.ModuleDict({
        'frontend': video_resnet(), 'proj_encoder': nn.Linear(512, 768),
        'encoder': ConformerEncoder(attention_dim=768, attention_heads=12, linear_units=3072,
                                   num_blocks=12, cnn_module_kernel=31),
    }).eval().requires_grad_(False)
    state = torch.load(root / 'r3/vlr/visual.pt', map_location='cpu', weights_only=True, mmap=True)
    network.load_state_dict(state, strict=True, assign=True)
    del state
    linears = {name for name, module in network.named_modules()
               if isinstance(module, nn.Linear) and any(part in ('feed_forward', 'feed_forward_macaron') for part in name.split('.'))}
    if quantized:
        if device != 'cpu' or len(linears) != 48:
            raise ValueError('Unexpected VLR CPU quantization contract')
        torch.ao.quantization.quantize_dynamic(network, linears, dtype=torch.qint8, inplace=True)
    network.to(device)

    def forward(frames):
        if frames.dtype != np.uint8 or frames.ndim != 3 or frames.shape[1:] != (96,96) or not len(frames):
            raise ValueError('Invalid VLR mouth crop')
        x = torch.from_numpy(frames[:,4:92,4:92].copy()).to(device=device, dtype=torch.float32)
        x = ((x / 255 - .421) / .165)[None,:,None]
        return network.encoder(network.proj_encoder(network.frontend(x)), None)[0][0].float().cpu().numpy()

    return network, forward, dict(precision='vlr-ffn-int8' if quantized else 'vlr-fp32',
                                  quantized_linears=len(linears) if quantized else 0)

