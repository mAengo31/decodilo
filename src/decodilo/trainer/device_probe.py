"""Trainer-facing device probe helpers."""

from __future__ import annotations

from decodilo.runtime.hardware_probe import probe_hardware


def available_devices() -> dict[str, bool | None]:
    probe = probe_hardware()
    return {
        "cpu": True,
        "cuda": probe.get("cuda_available"),
        "mps": probe.get("mps_available"),
    }

