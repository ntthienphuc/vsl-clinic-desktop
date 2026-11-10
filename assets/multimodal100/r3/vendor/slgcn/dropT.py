import torch
from torch import nn
import torch.nn.functional as F


class DropBlockT_1d(nn.Module):
    def __init__(self, block_size=7):
        super(DropBlockT_1d, self).__init__()
        self.keep_prob = 0.0
        self.block_size = block_size

    def forward(self, input, keep_prob):
        self.keep_prob = keep_prob
        if not self.training or self.keep_prob == 1:
            return input
        n, c, t, v = input.size()

        input_abs = torch.mean(torch.mean(torch.abs(input), dim=3), dim=1).detach()
        denom = torch.sum(input_abs).clamp_min(1e-6)
        input_abs = (input_abs / denom * input_abs.numel()).view(n, 1, t)
        input_abs = torch.nan_to_num(input_abs, nan=0.0, posinf=1.0, neginf=0.0)
        gamma = (1.0 - self.keep_prob) / self.block_size
        input1 = input.permute(0, 1, 3, 2).contiguous().view(n, c * v, t)
        probs = torch.clamp(input_abs * gamma, min=0.0, max=1.0)
        M = torch.bernoulli(probs).repeat(1, c * v, 1)
        Msum = F.max_pool1d(
            M, kernel_size=[self.block_size], stride=1, padding=self.block_size // 2
        )
        mask = (1 - Msum).to(device=input.device, dtype=input.dtype)
        mask_sum = mask.sum().clamp_min(1.0)
        return (
            (input1 * mask * mask.numel() / mask_sum)
            .view(n, c, v, t)
            .permute(0, 1, 3, 2)
        )
