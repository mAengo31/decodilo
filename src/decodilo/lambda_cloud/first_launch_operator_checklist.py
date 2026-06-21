"""Human operator checklist for final Lambda pre-launch review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaFirstLaunchOperatorChecklistItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    text: str
    acknowledged: bool = False
    required: bool = True


class LambdaFirstLaunchOperatorChecklist(BaseModel):
    model_config = ConfigDict(frozen=True)

    checklist_schema_version: int = 1
    checklist_id: str = "lambda-first-launch-operator-checklist-m025"
    items: list[LambdaFirstLaunchOperatorChecklistItem]
    review_only_complete: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFirstLaunchOperatorChecklist:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M025 operator checklist cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaFirstLaunchOperatorChecklistReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    checklist_complete_for_review: bool
    missing_items: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_first_launch_operator_checklist(
    *,
    acknowledge_all: bool = False,
) -> LambdaFirstLaunchOperatorChecklist:
    texts = {
        "billable_future": "I understand this may create billable resources in a future milestone.",
        "termination_verification": (
            "I understand termination must be verified through Lambda, not OS shutdown."
        ),
        "budget": "I understand max budget is 50 USD unless explicitly changed.",
        "runtime": "I understand max runtime is 30 minutes.",
        "one_instance": "I understand only one instance is allowed.",
        "no_training": "I understand no training workload will run during first launch.",
        "no_ssh_setup": "I understand no SSH/setup scripts unless later reviewed.",
        "operator_available": "I understand I must remain available during the launch window.",
        "m025_disabled": "I understand launch is still disabled in M025.",
        "ledger_review": "I have reviewed resource ledger and unmanaged resources.",
        "teardown_runbook": "I have reviewed teardown runbook.",
        "kill_switch": "I have reviewed kill-switch design.",
    }
    items = [
        LambdaFirstLaunchOperatorChecklistItem(
            item_id=item_id,
            text=text,
            acknowledged=acknowledge_all,
        )
        for item_id, text in texts.items()
    ]
    return LambdaFirstLaunchOperatorChecklist(
        items=items,
        review_only_complete=acknowledge_all,
    )


def evaluate_lambda_first_launch_operator_checklist(
    checklist: LambdaFirstLaunchOperatorChecklist,
) -> LambdaFirstLaunchOperatorChecklistReport:
    missing = [
        item.item_id for item in checklist.items if item.required and not item.acknowledged
    ]
    blockers = [f"missing operator acknowledgement: {item}" for item in missing]
    return LambdaFirstLaunchOperatorChecklistReport(
        checklist_complete_for_review=not blockers,
        missing_items=missing,
        blockers=blockers,
        warnings=["Checklist completion is review-only and does not enable launch."],
    )


def load_lambda_first_launch_operator_checklist(
    path: str | Path,
) -> LambdaFirstLaunchOperatorChecklist:
    return LambdaFirstLaunchOperatorChecklist.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_first_launch_operator_checklist(
    path: str | Path,
    checklist: LambdaFirstLaunchOperatorChecklist,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(checklist.to_json(), encoding="utf-8")
