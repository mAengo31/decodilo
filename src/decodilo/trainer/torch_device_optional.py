"""Optional single-device torch helpers."""

from __future__ import annotations

from decodilo.errors import InvariantViolation
from decodilo.trainer.torch_optional import require_torch


def validate_requested_torch_device(device: str, *, allow_accelerator: bool = False) -> str:
    torch = require_torch()
    if device == "cpu":
        return "cpu"
    if device.startswith("cuda"):
        if not allow_accelerator:
            raise InvariantViolation("cuda requires --allow-accelerator")
        if not torch.cuda.is_available():
            raise InvariantViolation("cuda requested but unavailable")
        return device
    if device == "mps":
        if not allow_accelerator:
            raise InvariantViolation("mps requires --allow-accelerator")
        mps = getattr(getattr(torch, "backends", None), "mps", None)
        if mps is None or not mps.is_available():
            raise InvariantViolation("mps requested but unavailable")
        return device
    raise InvariantViolation(f"unsupported device {device!r}")

