"""Review-only real teardown safety case for future Lambda mutation work."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.real_mutation_kill_switch_design import (
    LambdaKillSwitchDesign,
    build_lambda_kill_switch_design,
)
from decodilo.lambda_cloud.termination_verification_policy import (
    LambdaTerminationVerificationPolicy,
    build_lambda_termination_verification_policy,
)


class LambdaRealTeardownSafetyCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    safety_case_id: str = "lambda-real-teardown-safety-case-m023"
    design_only: bool = True
    termination_policy: LambdaTerminationVerificationPolicy
    kill_switch_design: LambdaKillSwitchDesign
    claims: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_termination_code_implemented: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _design_only(self) -> LambdaRealTeardownSafetyCase:
        if self.real_termination_code_implemented or self.launch_ready or self.launch_allowed:
            raise ValueError("M023 teardown safety case is design-only")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_real_teardown_safety_case(
    *,
    termination_policy: LambdaTerminationVerificationPolicy | None = None,
    kill_switch_design: LambdaKillSwitchDesign | None = None,
) -> LambdaRealTeardownSafetyCase:
    return LambdaRealTeardownSafetyCase(
        termination_policy=termination_policy or build_lambda_termination_verification_policy(),
        kill_switch_design=kill_switch_design or build_lambda_kill_switch_design(),
        claims=[
            "future termination can target only ledger-owned instance ids",
            "read-only verification is required after any future termination attempt",
            "OS shutdown is insufficient as a teardown signal",
            "unknown state requires manual review",
        ],
        warnings=["Design only; no real termination implementation exists in M023."],
    )


def load_lambda_real_teardown_safety_case(path: str | Path) -> LambdaRealTeardownSafetyCase:
    return LambdaRealTeardownSafetyCase.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_real_teardown_safety_case(
    path: str | Path,
    safety_case: LambdaRealTeardownSafetyCase,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(safety_case.to_json(), encoding="utf-8")
