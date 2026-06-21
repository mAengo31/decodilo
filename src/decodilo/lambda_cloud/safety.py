"""Lambda Cloud safety gate models for dry-run-only plans."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LambdaLaunchDisabledReason = Literal[
    "m018_offline_boundary_only",
    "real_lambda_api_disabled",
    "mutations_forbidden",
]


class LambdaSafetyGate(BaseModel):
    model_config = ConfigDict(frozen=True)

    launch_enabled: bool = False
    launch_allowed: bool = False
    launch_ready: bool = False
    teardown_enabled: bool = False
    mutation_guard_passed: bool = True
    live_api_used: bool = False
    disabled_reasons: list[LambdaLaunchDisabledReason] = Field(
        default_factory=lambda: [
            "m018_offline_boundary_only",
            "real_lambda_api_disabled",
            "mutations_forbidden",
        ]
    )
    warnings: list[str] = Field(default_factory=list)


def default_lambda_safety_gate() -> LambdaSafetyGate:
    return LambdaSafetyGate(
        warnings=[
            "M018 defines only an offline Lambda API boundary",
            "launch and teardown execution remain disabled",
        ]
    )
