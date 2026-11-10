import torch
from torch import nn


class DropBlock_Ske(nn.Module):
    def __init__(self, num_point, block_size=7):
        super(DropBlock_Ske, self).__init__()
        self.keep_prob = 0.0
        self.block_size = block_size
        self.num_point = num_point

    def forward(self, input, keep_prob, A):  # n,c,t,v
        self.keep_prob = keep_prob
        if not self.training or self.keep_prob == 1:
            return input
        n, c, t, v = input.size()

        input_abs = torch.mean(torch.mean(torch.abs(input), dim=2), dim=1).detach()
        denom = torch.sum(input_abs).clamp_min(1e-6)
        input_abs = input_abs / denom * input_abs.numel()
        input_abs = torch.nan_to_num(input_abs, nan=0.0, posinf=1.0, neginf=0.0)
        if self.num_point == 25:  # Kinect V2
            gamma = (1.0 - self.keep_prob) / (1 + 1.92)
        elif self.num_point == 20:  # Kinect V1
            gamma = (1.0 - self.keep_prob) / (1 + 1.9)
        else:
            gamma = (1.0 - self.keep_prob) / (1 + 1.92)

        probs = torch.clamp(input_abs * gamma, min=0.0, max=1.0)
        M_seed = torch.bernoulli(probs).to(
            device=input.device, dtype=input.dtype
        )
        M = torch.matmul(M_seed, A)
        M[M > 0.001] = 1.0
        M[M < 0.5] = 0.0
        mask = (1 - M).view(n, 1, 1, self.num_point)
        return input * mask * mask.numel() / mask.sum().clamp_min(1.0)
