"""Non-executable first real Lambda launch runbook for M025 review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaFirstLaunchRunbookStatus = Literal["draft", "review_ready", "blocked"]


class LambdaFirstLaunchRunbookStep(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: str
    section: str
    description: str
    non_executable: bool = True
    command_placeholder: str | None = None


class LambdaFirstLaunchRunbook(BaseModel):
    model_config = ConfigDict(frozen=True)

    runbook_schema_version: int = 1
    runbook_id: str = "lambda-first-launch-runbook-m025"
    status: LambdaFirstLaunchRunbookStatus = "review_ready"
    steps: list[LambdaFirstLaunchRunbookStep]
    constraints: list[str] = Field(default_factory=list)
    abort_conditions: list[str] = Field(default_factory=list)
    artifacts_to_collect: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    executable_launch_command_present: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _review_only(self) -> LambdaFirstLaunchRunbook:
        if self.executable_launch_command_present:
            raise ValueError("M025 runbook cannot contain executable launch commands")
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M025 runbook cannot enable mutation or launch")
        if any(not step.non_executable for step in self.steps):
            raise ValueError("all M025 runbook steps must be non-executable")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_first_launch_runbook() -> LambdaFirstLaunchRunbook:
    steps = [
        LambdaFirstLaunchRunbookStep(
            step_id="preconditions",
            section="preconditions",
            description="Verify M019C through M025 evidence before any future launch review.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="operator_presence",
            section="operator presence",
            description="Operator remains present for the entire future launch window.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="secret_handling",
            section="secret handling",
            description="Use only reviewed secret handling; do not print or serialize keys.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="budget_lock",
            section="budget lock",
            description="Confirm budget lock is present and max spend remains at or below 50 USD.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="launch_window",
            section="launch window",
            description="Confirm the bounded launch window is active and supervised.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="future_launch_placeholder",
            section="expected future command placeholders",
            description="Placeholder for a future reviewed launch command; non-executable in M025.",
            command_placeholder="<future-m026-launch-command>",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="post_launch_read_only_verification",
            section="immediate post-launch read-only verification",
            description="Verify owned instance by read-only list/get before any workload.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="runtime_timer",
            section="maximum runtime timer",
            description="Start a maximum 30 minute runtime timer immediately after future launch.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="mandatory_termination",
            section="mandatory termination sequence",
            description="Follow termination runbook before the timer expires.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="termination_verification",
            section="termination verification sequence",
            description="Verify terminal state with read-only Lambda discovery.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="failure_escalation",
            section="failure escalation",
            description="Stop and require manual review on unknown state or verification failure.",
        ),
        LambdaFirstLaunchRunbookStep(
            step_id="post_run_audit",
            section="post-run audit",
            description="Collect ledger, discovery, audit, termination, and spend evidence.",
        ),
    ]
    return LambdaFirstLaunchRunbook(
        steps=steps,
        constraints=[
            "no training workload",
            "no SSH",
            "no setup scripts",
            "one instance only",
            "max runtime 30 minutes",
            "max budget 50 USD",
            "M025 is review-only and cannot launch",
        ],
        abort_conditions=[
            "required evidence missing",
            "budget lock invalid",
            "unmanaged billable resources observed",
            "read-only verification unavailable",
            "operator unavailable",
        ],
        artifacts_to_collect=[
            "live discovery",
            "read-only audit",
            "resource ledger",
            "budget lock",
            "termination verification",
            "post-run audit",
        ],
        warnings=["Runbook is non-executable in M025."],
    )


def load_lambda_first_launch_runbook(path: str | Path) -> LambdaFirstLaunchRunbook:
    return LambdaFirstLaunchRunbook.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_first_launch_runbook(
    path: str | Path,
    runbook: LambdaFirstLaunchRunbook,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(runbook.to_json(), encoding="utf-8")
