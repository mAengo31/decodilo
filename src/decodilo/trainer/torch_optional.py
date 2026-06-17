"""Lazy optional PyTorch import helpers."""

from __future__ import annotations

from typing import Any

from decodilo.errors import OptionalDependencyMissing


def torch_available() -> bool:
    """Return whether PyTorch can be imported without importing it at module load."""

    try:
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


def require_torch() -> Any:
    """Import torch or raise a clear optional-dependency error."""

    try:
        import torch
    except ImportError as exc:
        raise OptionalDependencyMissing(
            "PyTorch is optional. Install it with `pip install -e '.[torch]'` "
            "to use torch trainer adapters."
        ) from exc
    return torch
