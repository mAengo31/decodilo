"""Model and optimizer state size estimators."""

from __future__ import annotations


def estimate_parameter_bytes(parameter_count: int, bytes_per_parameter: float) -> float:
    if parameter_count <= 0 or bytes_per_parameter <= 0:
        raise ValueError("parameter_count and bytes_per_parameter must be positive")
    return parameter_count * bytes_per_parameter


def estimate_optimizer_state_bytes(
    parameter_count: int,
    bytes_per_parameter: float,
    optimizer_multiplier: float,
) -> float:
    if optimizer_multiplier < 0:
        raise ValueError("optimizer_multiplier must be non-negative")
    return estimate_parameter_bytes(parameter_count, bytes_per_parameter) * optimizer_multiplier


def estimate_total_model_state_bytes(
    parameter_count: int,
    bytes_per_parameter: float,
    optimizer_multiplier: float,
) -> float:
    return estimate_parameter_bytes(
        parameter_count,
        bytes_per_parameter,
    ) + estimate_optimizer_state_bytes(parameter_count, bytes_per_parameter, optimizer_multiplier)


def human_readable_bytes(value: float) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{amount:.2f} PiB"

