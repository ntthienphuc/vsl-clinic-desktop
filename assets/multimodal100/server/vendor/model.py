# -*- coding: utf-8 -*-
"""Fusion revision: remove unavailable inputs before either cross-attention.

This revision requires new training. Historical checkpoints/results stay archived.
"""
import hashlib
import torch
from legacy_fusion import MultiModalFusionClassifier as Original, SequenceEncoder, AttentivePool

class MultiModalFusionClassifier(Original):
    def __init__(self,sign_dim,lip_dim,num_classes,d_model=96,num_heads=4,num_layers=1,dropout=.2,modality_dropout=.2,fusion='cross_attention',init_seed=None):
        torch.nn.Module.__init__(self)
        assert fusion in {'cross_attention','gated','concat'}
        self.fusion=fusion;self.modality_dropout=modality_dropout
        seed=int(torch.initial_seed() if init_seed is None else init_seed)
        # Preserve each component's default initialization distribution while
        # preventing the other encoder's input size from shifting its RNG stream.
        def make(name,factory):
            component_seed=int.from_bytes(hashlib.sha256(f'r3:{seed}:{name}'.encode()).digest()[:8],'big')%(2**63-1)
            with torch.random.fork_rng(devices=[]):
                torch.manual_seed(component_seed)
                return factory()
        nn=torch.nn
        self.sign_encoder=make('sign_encoder',lambda:SequenceEncoder(sign_dim,d_model,num_heads,num_layers,dropout))
        self.lip_encoder=make('lip_encoder',lambda:SequenceEncoder(lip_dim,d_model,num_heads,num_layers,dropout))
        self.cross_sign_to_lip=make('cross_sign_to_lip',lambda:nn.MultiheadAttention(d_model,num_heads,dropout=dropout,batch_first=True))
        self.cross_lip_to_sign=make('cross_lip_to_sign',lambda:nn.MultiheadAttention(d_model,num_heads,dropout=dropout,batch_first=True))
        self.pool=make('pool',lambda:AttentivePool(d_model))
        self.gate=make('gate',lambda:nn.Sequential(nn.LayerNorm(d_model*4+2),nn.Linear(d_model*4+2,d_model),nn.GELU(),nn.Dropout(dropout),nn.Linear(d_model,4)))
        self.classifier=make('classifier',lambda:nn.Sequential(nn.LayerNorm(d_model*7+2),nn.Linear(d_model*7+2,d_model*2),nn.GELU(),nn.Dropout(dropout),nn.Linear(d_model*2,num_classes)))
        self.initialization_policy='r3_component_seeded_default_distributions'

    def forward(self, sign, sign_mask, lip, lip_mask):
        sign_mask, lip_mask = sign_mask.bool(), lip_mask.bool()
        available = torch.stack([sign_mask.any(1), lip_mask.any(1)], 1)
        if not available.any(1).all():
            raise ValueError("Every sample needs at least one observed modality")
        if self.training and self.modality_dropout > 0:
            keep = (torch.rand(available.shape, device=sign.device) > self.modality_dropout) & available
            empty = ~keep.any(1)
            # Restore an actually observed stream, including lip-only examples.
            keep[empty, 0] = available[empty, 0]
            keep[empty, 1] = ~available[empty, 0] & available[empty, 1]
            available = keep
        sign_mask = sign_mask & available[:, 0, None]
        lip_mask = lip_mask & available[:, 1, None]

        def encode(encoder, values, mask):
            values = torch.where(mask.unsqueeze(-1), values, torch.zeros_like(values))
            if not torch.isfinite(values).all():
                raise ValueError("Non-finite observed features")
            safe_mask = mask.clone()
            safe_mask[~safe_mask.any(1), 0] = True
            result = encoder(values, safe_mask)
            return torch.where(mask.unsqueeze(-1), result, torch.zeros_like(result))

        se = encode(self.sign_encoder, sign, sign_mask)
        le = encode(self.lip_encoder, lip, lip_mask)
        sp, lp = self.pool(se, sign_mask), self.pool(le, lip_mask)
        sc, lc = torch.zeros_like(sp), torch.zeros_like(lp)
        both = available.all(1)
        cross_valid = both & (self.fusion == "cross_attention")
        if cross_valid.any():
            index = cross_valid.nonzero(as_tuple=True)[0]
            sx, lx = se[index], le[index]
            sm, lm = sign_mask[index], lip_mask[index]
            sx2, _ = self.cross_sign_to_lip(sx, lx, lx, key_padding_mask=~lm, need_weights=False)
            lx2, _ = self.cross_lip_to_sign(lx, sx, sx, key_padding_mask=~sm, need_weights=False)
            sc = sc.index_copy(0, index, self.pool(sx2, sm))
            lc = lc.index_copy(0, index, self.pool(lx2, lm))
        av = available.to(sp.dtype)
        components = torch.stack([sp, lp, sc, lc], 1)
        valid = torch.stack([available[:,0], available[:,1], cross_valid, cross_valid], 1)
        gate_input = torch.cat([sp, lp, sc, lc, av], -1)
        weights = self.gate(gate_input).masked_fill(~valid, -torch.inf).softmax(-1)
        fused = (components * weights.unsqueeze(-1)).sum(1)
        if self.fusion == "concat":
            fused = (sp + lp) / av.sum(1, keepdim=True)
        return self.classifier(torch.cat([fused, sp, lp, sc, lc, (sp-lp).abs(), sp*lp, av], -1))
