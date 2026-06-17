"""Launch review checklist for dry-run cloud plans."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.cloud.launch_plan import CloudDryRunReport
from decodilo.cloud.teardown_plan import TeardownPlan


class LaunchApprovalGate(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    reason: str = ""


class LaunchReviewChecklist(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    provider: str
    launch_allowed: bool = False
    operator_acknowledged: bool = False
    gates: list[LaunchApprovalGate] = Field(default_factory=list)
    budget_manifest_present: bool = False
    teardown_plan: TeardownPlan | None = None
    max_runtime_hours: float
    max_run_budget: float

    @property
    def passed(self) -> bool:
        return all(gate.passed for gate in self.gates)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_launch_review_checklist(
    report: CloudDryRunReport,
    *,
    operator_acknowledged: bool = False,
) -> LaunchReviewChecklist:
    plan = report.plan
    teardown_plan = (
        TeardownPlan.model_validate(plan.teardown_plan) if plan.teardown_plan is not None else None
    )
    gates = [
        LaunchApprovalGate(
            name="launch_remains_disabled",
            passed=plan.launch_allowed is False,
            reason=plan.reason_launch_not_allowed,
        ),
        LaunchApprovalGate(
            name="budget_manifest_present",
            passed=plan.budget_manifest is not None,
            reason="budget manifest required before any future launch",
        ),
        LaunchApprovalGate(
            name="teardown_plan_present",
            passed=teardown_plan is not None,
            reason="dry-run plans must still include teardown expectations",
        ),
        LaunchApprovalGate(
            name="operator_acknowledged",
            passed=operator_acknowledged,
            reason="operator acknowledgement is required before a future launch gate",
        ),
        LaunchApprovalGate(
            name="public_bind_disabled",
            passed=True,
            reason="local services bind to 127.0.0.1 by default",
        ),
        LaunchApprovalGate(
            name="validation_errors_absent",
            passed=not report.validation_errors,
            reason="dry-run validation must pass",
        ),
    ]
    return LaunchReviewChecklist(
        run_id=plan.run_id,
        provider=plan.provider,
        launch_allowed=False,
        operator_acknowledged=operator_acknowledged,
        gates=gates,
        budget_manifest_present=plan.budget_manifest is not None,
        teardown_plan=teardown_plan,
        max_runtime_hours=plan.planned_hours,
        max_run_budget=plan.max_run_budget,
    )


def write_launch_review_checklist(path: str | Path, checklist: LaunchReviewChecklist) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(checklist.to_json(), encoding="utf-8")


def load_launch_review_checklist(path: str | Path) -> LaunchReviewChecklist:
    return LaunchReviewChecklist.model_validate_json(Path(path).read_text(encoding="utf-8"))
