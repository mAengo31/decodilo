"""Aggregate M090 closeout report for the first bounded synthetic DiLoCo run."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bounded_diloco_experiment_artifact_audit import (
    load_lambda_bounded_diloco_experiment_artifact_audit,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_closeout import (
    load_lambda_bounded_diloco_experiment_closeout,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_reconciliation import (
    load_lambda_bounded_diloco_experiment_reconciliation,
)
from decodilo.lambda_cloud.bounded_diloco_experiment_success_record import (
    load_lambda_bounded_diloco_experiment_success_record,
)
from decodilo.lambda_cloud.post_m089_next_step_decision import (
    load_lambda_post_m089_next_step_decision,
)
from decodilo.lambda_cloud.scaffold_completion_final_decision import (
    load_lambda_scaffold_completion_final_decision,
)
from decodilo.lambda_cloud.scientific_gap_assessment import (
    load_lambda_scientific_gap_assessment,
)


class LambdaM090Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M090"
    report_passed: bool
    bounded_success_status: str
    bounded_closeout_status: str
    bounded_closeout_succeeded: bool
    reconciliation_passed: bool
    bounded_artifact_audit_passed: bool
    artifact_sha256: str | None = None
    optimization_fidelity: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    parameter_fragment_semantics: str | None = None
    learners_observed: int | None = None
    sync_rounds_completed: int | None = None
    fragments_observed: int | None = None
    max_abs_error: float | None = None
    scaffold_final_status: str
    bounded_experiment_completed: bool
    scientific_gap_assessment_status: str
    remaining_scientific_gaps: list[str] = Field(default_factory=list)
    recommended_next_path: str
    no_new_live_authorization: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM090Report:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M090 report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M090 report cannot carry blockers")
        if self.no_new_live_authorization is not True:
            raise ValueError("M090 report must not create live authorization")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m090_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    artifact_audit: str | Path,
    scaffold_final_decision: str | Path,
    scientific_gap_assessment: str | Path,
    next_step_decision: str | Path,
) -> LambdaM090Report:
    record = load_lambda_bounded_diloco_experiment_success_record(success_record)
    reconcile = load_lambda_bounded_diloco_experiment_reconciliation(reconciliation)
    closeout_report = load_lambda_bounded_diloco_experiment_closeout(closeout)
    audit = load_lambda_bounded_diloco_experiment_artifact_audit(artifact_audit)
    scaffold = load_lambda_scaffold_completion_final_decision(
        scaffold_final_decision
    )
    gaps = load_lambda_scientific_gap_assessment(scientific_gap_assessment)
    decision = load_lambda_post_m089_next_step_decision(next_step_decision)
    blockers: list[str] = []
    if (
        record.success_status
        != "remote_bounded_synthetic_diloco_experiment_success"
    ):
        blockers.append("bounded_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("bounded_reconciliation_not_passed")
    if not closeout_report.closeout_succeeded:
        blockers.append("bounded_closeout_not_succeeded")
    if not audit.artifact_audit_passed:
        blockers.append("bounded_artifact_audit_not_passed")
    if scaffold.scaffold_final_status != "complete":
        blockers.append("scaffold_final_status_not_complete")
    if gaps.assessment_status != "scientific_gaps_assessed":
        blockers.append("scientific_gap_assessment_not_passed")
    if not decision.no_automatic_live_authorization:
        blockers.append("next_step_authorized_live_run")
    return LambdaM090Report(
        report_passed=not blockers,
        bounded_success_status=record.success_status,
        bounded_closeout_status=closeout_report.closeout_status,
        bounded_closeout_succeeded=closeout_report.closeout_succeeded,
        reconciliation_passed=reconcile.reconciliation_passed,
        bounded_artifact_audit_passed=audit.artifact_audit_passed,
        artifact_sha256=audit.artifact_sha256,
        optimization_fidelity=record.optimization_fidelity,
        inner_optimizer_semantics=record.inner_optimizer_semantics,
        outer_optimizer_semantics=record.outer_optimizer_semantics,
        parameter_fragment_semantics=record.parameter_fragment_semantics,
        learners_observed=record.learners_observed,
        sync_rounds_completed=record.sync_rounds_completed,
        fragments_observed=record.fragments_observed,
        max_abs_error=record.max_abs_error,
        scaffold_final_status=scaffold.scaffold_final_status,
        bounded_experiment_completed=scaffold.bounded_experiment_completed,
        scientific_gap_assessment_status=gaps.assessment_status,
        remaining_scientific_gaps=gaps.remaining_gaps,
        recommended_next_path=decision.recommended_path,
        no_new_live_authorization=decision.no_automatic_live_authorization,
        historical_billable_action_performed=(
            record.historical_billable_action_performed
        ),
        blockers=blockers,
        warnings=[
            "M090 is offline and creates no future live authorization",
            "scaffold validation is complete; future milestones should be chosen "
            "from explicit scientific gaps",
        ],
    )


def load_lambda_m090_report(path: str | Path) -> LambdaM090Report:
    return LambdaM090Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m090_report(path: str | Path, report: LambdaM090Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
