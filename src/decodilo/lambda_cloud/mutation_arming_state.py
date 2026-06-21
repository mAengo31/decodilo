"""Unarmed mutation state for the disabled Lambda mutation skeleton."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaMutationArmingState(BaseModel):
    model_config = ConfigDict(frozen=True)

    state_schema_version: int = 1
    arming_state_id: str = "lambda-mutation-arming-state-m024"
    mutation_armed: bool = False
    arming_allowed: bool = False
    armed_by: str | None = None
    armed_at_utc: str | None = None
    reason_unarmed: str = "M024 skeleton cannot be armed."
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _cannot_arm(self) -> LambdaMutationArmingState:
        if (
            self.mutation_armed
            or self.arming_allowed
            or self.real_mutation_enabled
            or self.launch_ready
            or self.launch_allowed
        ):
            raise ValueError("M024 mutation arming state cannot arm or enable execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaMutationArmingStateReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    arming_state: LambdaMutationArmingState = Field(default_factory=LambdaMutationArmingState)
    arming_state_valid: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_lambda_mutation_arming_state(
    state: LambdaMutationArmingState | None = None,
) -> LambdaMutationArmingStateReport:
    effective = state or LambdaMutationArmingState()
    blockers: list[str] = []
    if effective.mutation_armed:
        blockers.append("mutation arming is forbidden in M024")
    return LambdaMutationArmingStateReport(
        arming_state=effective,
        arming_state_valid=not blockers,
        blockers=blockers,
        warnings=["Mutation arming remains disabled in M024."],
    )


def load_lambda_mutation_arming_state(path: str | Path) -> LambdaMutationArmingState:
    return LambdaMutationArmingState.model_validate_json(Path(path).read_text(encoding="utf-8"))
