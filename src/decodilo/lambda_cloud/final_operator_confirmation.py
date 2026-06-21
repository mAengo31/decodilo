"""M028 final operator confirmation package."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaFinalOperatorConfirmation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    confirmation_id: str = "lambda-final-operator-confirmation-m028"
    operator_name: str | None = None
    understands_m028_does_not_launch: bool = False
    understands_m029_may_launch_billable_instance: bool = False
    understands_max_budget_50: bool = False
    understands_max_runtime_30_min: bool = False
    understands_one_instance_only: bool = False
    understands_termination_must_be_verified: bool = False
    understands_os_shutdown_insufficient: bool = False
    understands_no_training: bool = False
    understands_no_ssh_or_setup_scripts: bool = False
    will_remain_present: bool = False
    accepts_manual_review_on_teardown_failure: bool = False
    requested_max_budget: float = 50.0
    requested_max_runtime_minutes: int = 30
    requested_max_instances: int = 1
    confirmation_complete_for_m029_authorization: bool = False
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaFinalOperatorConfirmation:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("operator confirmation cannot enable launch or mutation")
        if self.requested_max_budget > 50:
            raise ValueError("operator confirmation budget exceeds 50 USD")
        if self.requested_max_runtime_minutes > 30:
            raise ValueError("operator confirmation runtime exceeds 30 minutes")
        if self.requested_max_instances > 1:
            raise ValueError("operator confirmation instances exceed one")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaFinalOperatorConfirmationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    confirmation: LambdaFinalOperatorConfirmation
    confirmation_passed: bool
    missing_acknowledgements: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    billable_action_performed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


_ACK_FIELDS = [
    "understands_m028_does_not_launch",
    "understands_m029_may_launch_billable_instance",
    "understands_max_budget_50",
    "understands_max_runtime_30_min",
    "understands_one_instance_only",
    "understands_termination_must_be_verified",
    "understands_os_shutdown_insufficient",
    "understands_no_training",
    "understands_no_ssh_or_setup_scripts",
    "will_remain_present",
    "accepts_manual_review_on_teardown_failure",
]


def build_lambda_final_operator_confirmation_template(
    *,
    acknowledge_all: bool = False,
) -> LambdaFinalOperatorConfirmation:
    values = {field: acknowledge_all for field in _ACK_FIELDS}
    return LambdaFinalOperatorConfirmation(
        **values,
        confirmation_complete_for_m029_authorization=acknowledge_all,
    )


def evaluate_lambda_final_operator_confirmation(
    confirmation: str | Path | LambdaFinalOperatorConfirmation,
) -> LambdaFinalOperatorConfirmationReport:
    value = (
        confirmation
        if isinstance(confirmation, LambdaFinalOperatorConfirmation)
        else load_lambda_final_operator_confirmation(confirmation)
    )
    missing = [field for field in _ACK_FIELDS if not getattr(value, field)]
    blockers = [f"missing acknowledgement: {field}" for field in missing]
    if not value.confirmation_complete_for_m029_authorization:
        blockers.append("operator confirmation is not marked complete")
    return LambdaFinalOperatorConfirmationReport(
        confirmation=value,
        confirmation_passed=not blockers,
        missing_acknowledgements=missing,
        blockers=blockers,
        warnings=["Operator confirmation authorizes M029 package only, not M028 launch."],
    )


def load_lambda_final_operator_confirmation(
    path: str | Path,
) -> LambdaFinalOperatorConfirmation:
    return LambdaFinalOperatorConfirmation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_final_operator_confirmation(
    path: str | Path,
    confirmation: LambdaFinalOperatorConfirmation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(confirmation.to_json(), encoding="utf-8")

