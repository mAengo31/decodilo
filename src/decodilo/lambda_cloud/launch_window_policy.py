"""Design-only launch window policy for future first Lambda launch review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaLaunchWindowPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_schema_version: int = 1
    policy_id: str = "lambda-launch-window-policy-m023"
    design_only: bool = True
    max_window_minutes: int = Field(default=30, gt=0)
    require_manual_operator_present: bool = True
    require_no_background_work: bool = True
    require_budget_deadline: bool = True
    require_runtime_deadline: bool = True
    require_kill_switch_visible: bool = True
    window_active: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _prevent_active_launch_window(self) -> LambdaLaunchWindowPolicy:
        if self.window_active or self.launch_ready or self.launch_allowed:
            raise ValueError("M023 launch window policy cannot activate launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaLaunchWindowPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    policy: LambdaLaunchWindowPolicy
    policy_passed_for_design_review: bool
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_lambda_launch_window_policy(
    policy: LambdaLaunchWindowPolicy | None = None,
) -> LambdaLaunchWindowPolicyReport:
    effective = policy or LambdaLaunchWindowPolicy()
    violations: list[str] = []
    if effective.max_window_minutes > 30:
        violations.append("launch window exceeds 30 minutes")
    if not effective.require_manual_operator_present:
        violations.append("manual operator presence is required")
    if not effective.require_no_background_work:
        violations.append("background work must be forbidden")
    return LambdaLaunchWindowPolicyReport(
        policy=effective,
        policy_passed_for_design_review=not violations,
        violations=violations,
        warnings=["Launch window is design-only; no launch can be activated in M023."],
    )


def load_lambda_launch_window_policy(path: str | Path) -> LambdaLaunchWindowPolicy:
    return LambdaLaunchWindowPolicy.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_launch_window_policy(path: str | Path, policy: LambdaLaunchWindowPolicy) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
