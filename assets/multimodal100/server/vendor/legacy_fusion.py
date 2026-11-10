import math

import torch
import torch.nn as nn


class SinusoidalPositionEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 4096) -> None:
        super().__init__()
        position = torch.arange(max_len, dtype=torch.float32).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2, dtype=torch.float32) * (-math.log(10000.0) / d_model))
        pe = torch.zeros(max_len, d_model, dtype=torch.float32)
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0), persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if x.shape[1] > self.pe.shape[1]:
            raise ValueError(f"Sequence length {x.shape[1]} exceeds max positional length {self.pe.shape[1]}")
        return x + self.pe[:, :x.shape[1]].to(dtype=x.dtype)


class SequenceEncoder(nn.Module):
    def __init__(self, in_dim: int, d_model: int, num_heads: int, num_layers: int, dropout: float) -> None:
        super().__init__()
        self.proj = nn.Sequential(
            nn.Linear(in_dim, d_model),
            nn.LayerNorm(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.pos = SinusoidalPositionEncoding(d_model)
        layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=num_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        x = self.proj(x)
        x = self.pos(x)
        encoded = self.encoder(x, src_key_padding_mask=~mask)
        return self.norm(encoded)


class AttentivePool(nn.Module):
    def __init__(self, d_model: int) -> None:
        super().__init__()
        self.score = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, 1),
        )

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        scores = self.score(x).squeeze(-1)
        scores = scores.masked_fill(~mask, torch.finfo(scores.dtype).min)
        weights = torch.softmax(scores, dim=-1)
        weights = torch.where(mask, weights, torch.zeros_like(weights))
        denom = weights.sum(dim=-1, keepdim=True).clamp_min(1e-6)
        weights = weights / denom
        return torch.bmm(weights.unsqueeze(1), x).squeeze(1)


class MultiModalFusionClassifier(nn.Module):
    def __init__(
        self,
        sign_dim: int,
        lip_dim: int,
        num_classes: int,
        d_model: int = 384,
        num_heads: int = 6,
        num_layers: int = 2,
        dropout: float = 0.2,
        modality_dropout: float = 0.15,
        fusion: str = "cross_attention",
    ) -> None:
        super().__init__()
        if fusion not in {"cross_attention", "gated", "concat"}:
            raise ValueError(f"Unsupported fusion: {fusion}")
        self.fusion = fusion
        self.modality_dropout = modality_dropout
        self.sign_encoder = SequenceEncoder(sign_dim, d_model, num_heads, num_layers, dropout)
        self.lip_encoder = SequenceEncoder(lip_dim, d_model, num_heads, num_layers, dropout)
        self.cross_sign_to_lip = nn.MultiheadAttention(d_model, num_heads, dropout=dropout, batch_first=True)
        self.cross_lip_to_sign = nn.MultiheadAttention(d_model, num_heads, dropout=dropout, batch_first=True)
        self.pool = AttentivePool(d_model)
        self.gate = nn.Sequential(
            nn.LayerNorm(d_model * 4 + 2),
            nn.Linear(d_model * 4 + 2, d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model, 4),
        )
        classifier_dim = d_model * 7 + 2
        self.classifier = nn.Sequential(
            nn.LayerNorm(classifier_dim),
            nn.Linear(classifier_dim, d_model * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_model * 2, num_classes),
        )

    def _apply_modality_dropout(
        self,
        sign_pool: torch.Tensor,
        lip_pool: torch.Tensor,
        sign_cross: torch.Tensor,
        lip_cross: torch.Tensor,
        availability: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if not self.training or self.modality_dropout <= 0:
            return sign_pool, lip_pool, sign_cross, lip_cross, availability
        batch = availability.shape[0]
        keep_sign = torch.rand(batch, device=availability.device) > self.modality_dropout
        keep_lip = torch.rand(batch, device=availability.device) > self.modality_dropout
        both_dropped = ~keep_sign & ~keep_lip
        keep_sign = keep_sign | both_dropped
        keep = torch.stack([keep_sign, keep_lip], dim=-1).to(availability.dtype)
        availability = availability * keep
        sign_keep = keep[:, :1]
        lip_keep = keep[:, 1:2]
        sign_pool = sign_pool * sign_keep
        sign_cross = sign_cross * sign_keep
        lip_pool = lip_pool * lip_keep
        lip_cross = lip_cross * lip_keep
        return sign_pool, lip_pool, sign_cross, lip_cross, availability

    def forward(
        self,
        sign: torch.Tensor,
        sign_mask: torch.Tensor,
        lip: torch.Tensor,
        lip_mask: torch.Tensor,
    ) -> torch.Tensor:
        sign_encoded = self.sign_encoder(sign, sign_mask)
        lip_encoded = self.lip_encoder(lip, lip_mask)
        sign_pool = self.pool(sign_encoded, sign_mask)
        lip_pool = self.pool(lip_encoded, lip_mask)

        if self.fusion == "cross_attention":
            sign_cross_seq, _ = self.cross_sign_to_lip(
                query=sign_encoded,
                key=lip_encoded,
                value=lip_encoded,
                key_padding_mask=~lip_mask,
                need_weights=False,
            )
            lip_cross_seq, _ = self.cross_lip_to_sign(
                query=lip_encoded,
                key=sign_encoded,
                value=sign_encoded,
                key_padding_mask=~sign_mask,
                need_weights=False,
            )
            sign_cross = self.pool(sign_cross_seq, sign_mask)
            lip_cross = self.pool(lip_cross_seq, lip_mask)
        elif self.fusion == "gated":
            sign_cross = torch.zeros_like(sign_pool)
            lip_cross = torch.zeros_like(lip_pool)
        else:
            sign_cross = torch.zeros_like(sign_pool)
            lip_cross = torch.zeros_like(lip_pool)

        availability = torch.stack(
            [sign_mask.any(dim=1).float(), lip_mask.any(dim=1).float()],
            dim=-1,
        ).to(sign_pool.device)
        sign_pool, lip_pool, sign_cross, lip_cross, availability = self._apply_modality_dropout(
            sign_pool, lip_pool, sign_cross, lip_cross, availability
        )

        components = torch.stack([sign_pool, lip_pool, sign_cross, lip_cross], dim=1)
        gate_input = torch.cat([sign_pool, lip_pool, sign_cross, lip_cross, availability], dim=-1)
        gates = torch.softmax(self.gate(gate_input), dim=-1).unsqueeze(-1)
        fused = (components * gates).sum(dim=1)

        if self.fusion == "concat":
            fused = 0.5 * (sign_pool + lip_pool)
        classifier_input = torch.cat(
            [
                fused,
                sign_pool,
                lip_pool,
                sign_cross,
                lip_cross,
                torch.abs(sign_pool - lip_pool),
                sign_pool * lip_pool,
                availability,
            ],
            dim=-1,
        )
        return self.classifier(classifier_input)
