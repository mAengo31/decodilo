"""Optional torch metric helpers with lazy torch imports."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from decodilo.trainer.torch_optional import require_torch


@dataclass(frozen=True)
class TorchStepMetrics:
    loss_before: float | None
    loss_after: float | None
    grad_norm: float | None
    num_parameters: int
    nonfinite_detected: bool


def tensor_is_finite(tensor: Any) -> bool:
    torch = require_torch()
    return bool(torch.isfinite(tensor.detach()).all().item())


def module_has_nonfinite(module: Any) -> bool:
    return any(not tensor_is_finite(parameter) for parameter in module.parameters())


def module_num_parameters(module: Any) -> int:
    return int(sum(parameter.numel() for parameter in module.parameters()))


def compute_grad_norm(module: Any) -> float | None:
    torch = require_torch()
    total = torch.tensor(0.0)
    found = False
    for parameter in module.parameters():
        if parameter.grad is None:
            continue
        found = True
        total = total + torch.sum(parameter.grad.detach().float() ** 2).cpu()
    if not found:
        return None
    value = float(torch.sqrt(total).item())
    if not math.isfinite(value):
        return value
    return value
