"""Disabled-by-design mutation transport specification for M023."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaDisabledMutationTransportSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    spec_id: str = "lambda-disabled-mutation-transport-spec-m023"
    intended_future_methods: list[str] = Field(
        default_factory=lambda: [
            "launch_one_instance",
            "terminate_owned_instance",
        ]
    )
    disabled_in_current_build: bool = True
    reason_disabled: str = "M023 is review-only; no real mutation transport is implemented."
    required_future_guards: list[str] = Field(
        default_factory=lambda: [
            "endpoint allowlist",
            "mutation arming gate",
            "budget gate",
            "approval gate",
            "resource ledger ownership check",
            "idempotency key",
            "termination verification policy",
        ]
    )
    forbidden_until_milestone: str = "after M023 design review"
    no_code_implemented: bool = True
    executable_transport_available: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _must_remain_disabled(self) -> LambdaDisabledMutationTransportSpec:
        if (
            not self.disabled_in_current_build
            or not self.no_code_implemented
            or self.executable_transport_available
            or self.real_mutation_enabled
            or self.launch_ready
            or self.launch_allowed
        ):
            raise ValueError("disabled mutation transport spec cannot be executable in M023")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_disabled_mutation_transport_spec() -> LambdaDisabledMutationTransportSpec:
    return LambdaDisabledMutationTransportSpec()


def load_lambda_disabled_mutation_transport_spec(
    path: str | Path,
) -> LambdaDisabledMutationTransportSpec:
    return LambdaDisabledMutationTransportSpec.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_disabled_mutation_transport_spec(
    path: str | Path,
    spec: LambdaDisabledMutationTransportSpec,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(spec.to_json(), encoding="utf-8")
