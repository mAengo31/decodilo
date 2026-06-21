"""M052 closeout report for successful metadata-only Lambda bootstrap."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m053_next_step_decision import (
    load_lambda_m053_next_step_decision,
)
from decodilo.lambda_cloud.metadata_bootstrap_closeout import (
    load_lambda_metadata_bootstrap_closeout,
)
from decodilo.lambda_cloud.metadata_bootstrap_lifecycle_comparison import (
    load_lambda_metadata_bootstrap_lifecycle_comparison,
)
from decodilo.lambda_cloud.metadata_bootstrap_reconciliation import (
    load_lambda_metadata_bootstrap_reconciliation,
)
from decodilo.lambda_cloud.metadata_bootstrap_success_record import (
    load_lambda_metadata_bootstrap_success_record,
)
from decodilo.lambda_cloud.no_remote_execution_attestation import (
    load_lambda_no_remote_execution_attestation,
)
from decodilo.lambda_cloud.remote_bootstrap_strategy_update import (
    load_lambda_remote_bootstrap_strategy_update,
)


class LambdaM052Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    success_record_status: str
    reconciliation_status: str
    closeout_status: str
    no_remote_execution_attestation_status: str
    lifecycle_comparison_status: str
    strategy_update_status: str
    m053_decision: str
    selected_candidate: str | None = None
    selected_region: str | None = None
    report_passed: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaM052Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M052 report cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m052_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    no_remote_execution_attestation: str | Path,
    comparison: str | Path,
    strategy_update: str | Path,
    decision: str | Path,
) -> LambdaM052Report:
    success = load_lambda_metadata_bootstrap_success_record(success_record)
    reconcile = load_lambda_metadata_bootstrap_reconciliation(reconciliation)
    close = load_lambda_metadata_bootstrap_closeout(closeout)
    no_remote = load_lambda_no_remote_execution_attestation(
        no_remote_execution_attestation
    )
    compare = load_lambda_metadata_bootstrap_lifecycle_comparison(comparison)
    strategy = load_lambda_remote_bootstrap_strategy_update(strategy_update)
    next_decision = load_lambda_m053_next_step_decision(decision)
    blockers = [
        *success.blockers,
        *reconcile.errors,
        *close.blockers,
        *no_remote.blockers,
        *compare.blockers,
        *strategy.blockers,
        *next_decision.blockers,
    ]
    if success.status != "metadata_bootstrap_success":
        blockers.append("metadata_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("metadata_reconciliation_not_passed")
    if not close.closeout_succeeded:
        blockers.append("metadata_closeout_not_succeeded")
    if not no_remote.attestation_passed:
        blockers.append("no_remote_execution_attestation_failed")
    if not strategy.metadata_bootstrap_successful:
        blockers.append("strategy_update_not_successful")
    return LambdaM052Report(
        success_record_status=success.status,
        reconciliation_status="passed" if reconcile.reconciliation_passed else "blocked",
        closeout_status=close.closeout_status,
        no_remote_execution_attestation_status=(
            "passed" if no_remote.attestation_passed else "blocked"
        ),
        lifecycle_comparison_status=(
            "passed" if not compare.blockers else "blocked"
        ),
        strategy_update_status=strategy.recommended_next_stage,
        m053_decision=next_decision.decision_status,
        selected_candidate=success.selected_candidate,
        selected_region=success.selected_region,
        report_passed=not blockers,
        historical_billable_action_performed=success.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M052 is closeout-only and performs no Lambda operation",
                    *success.warnings,
                    *reconcile.warnings,
                    *close.warnings,
                    *no_remote.warnings,
                    *compare.warnings,
                    *strategy.warnings,
                    *next_decision.warnings,
                ]
            )
        ),
    )


def load_lambda_m052_report(path: str | Path) -> LambdaM052Report:
    return LambdaM052Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m052_report(path: str | Path, report: LambdaM052Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
