"""Optional local hardware probing without making accelerators a dependency."""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

from decodilo.trainer.torch_optional import torch_available


def probe_hardware(*, requested_device: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "cpu_available": True,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or None,
        "torch_available": torch_available(),
        "cuda_available": None,
        "cuda_device_count": None,
        "mps_available": None,
        "selected_device": requested_device or "cpu",
        "warnings": [],
    }
    if result["torch_available"]:
        from decodilo.trainer.torch_optional import require_torch

        torch = require_torch()
        result["cuda_available"] = bool(torch.cuda.is_available())
        result["cuda_device_count"] = (
            int(torch.cuda.device_count()) if torch.cuda.is_available() else 0
        )
        mps = getattr(getattr(torch, "backends", None), "mps", None)
        result["mps_available"] = bool(mps is not None and mps.is_available())
    else:
        result["warnings"].append("torch is not installed; accelerator availability not probed")
    return result


def write_hardware_probe(path: str | Path, payload: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
