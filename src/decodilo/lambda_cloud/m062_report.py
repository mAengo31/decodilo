"""M062 offline closeout and future M063 GPU visibility review report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_command_policy import (
    load_lambda_gpu_visibility_command_policy,
)
from decodilo.lambda_cloud.gpu_visibility_command_review import (
    load_lambda_gpu_visibility_command_review,
)
from decodilo.lambda_cloud.gpu_visibility_output_policy import (
    load_lambda_gpu_visibility_output_policy,
)
from decodilo.lambda_cloud.m063_gpu_visibility_authorization import (
    load_lambda_m063_gpu_visibility_authorization,
)
from decodilo.lambda_cloud.m063_gpu_visibility_runbook_preview import (
    load_lambda_m063_gpu_visibility_runbook_preview,
)
from decodilo.lambda_cloud.whoami_command_closeout import (
    load_lambda_whoami_command_closeout,
)
from decodilo.lambda_cloud.whoami_command_reconciliation import (
    load_lambda_whoami_command_reconciliation,
)
from decodilo.lambda_cloud.whoami_command_success_record import (
    load_lambda_whoami_command_success_record,
)


class LambdaM062Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    success_record_status: str
    reconciliation_status: str
    evidence_complete: bool
    closeout_status: str
    command_policy_status: str
    output_policy_status: str
    command_review_status: str
    m063_authorization_status: str
    runbook_preview_status: str
    selected_future_command_set: list[str] = Field(default_factory=list)
    selected_candidate: str | None = None
    selected_region: str | None = None
    historical_billable_action_performed: bool
    m062_billable_action_performed: bool = False
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaM062Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.m062_billable_action_performed
        ):
            raise ValueError("M062 report cannot enable launch, mutation, or spend")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m062_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    evidence_package: str | Path,
    closeout: str | Path,
    command_policy: str | Path,
    output_policy: str | Path,
    command_review: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM062Report:
    success = load_lambda_whoami_command_success_record(success_record)
    reconcile = load_lambda_whoami_command_reconciliation(reconciliation)
    evidence_data = json.loads(Path(evidence_package).read_text(encoding="utf-8"))
    close = load_lambda_whoami_command_closeout(closeout)
    command = load_lambda_gpu_visibility_command_policy(command_policy)
    output = load_lambda_gpu_visibility_output_policy(output_policy)
    review = load_lambda_gpu_visibility_command_review(command_review)
    auth = load_lambda_m063_gpu_visibility_authorization(authorization)
    runbook = load_lambda_m063_gpu_visibility_runbook_preview(runbook_preview)
    blockers = [
        *success.blockers,
        *reconcile.errors,
        *close.blockers,
        *command.blockers,
        *output.blockers,
        *review.blockers,
        *auth.blockers,
        *runbook.blockers,
    ]
    evidence_complete = bool(evidence_data.get("evidence_complete"))
    if success.status != "whoami_command_success":
        blockers.append("whoami_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("whoami_reconciliation_not_passed")
    if not evidence_complete:
        blockers.append("whoami_evidence_package_incomplete")
    if not close.closeout_succeeded:
        blockers.append("whoami_closeout_not_succeeded")
    if (
        command.command_policy_status
        != "gpu_visibility_command_policy_defined_future_only"
    ):
        blockers.append("gpu_visibility_command_policy_not_ready")
    if output.output_policy_status != "gpu_visibility_output_policy_defined_future_only":
        blockers.append("gpu_visibility_output_policy_not_ready")
    if review.command_review_status != "gpu_visibility_command_review_passed_future_only":
        blockers.append("gpu_visibility_command_review_not_ready")
    if (
        auth.authorization_status
        != "authorized_for_future_m063_gpu_visibility_query_review"
    ):
        blockers.append("m063_authorization_not_ready")
    if runbook.preview_status != "ready_for_future_m063_gpu_visibility_query_review":
        blockers.append("m063_runbook_preview_not_ready")
    return LambdaM062Report(
        success_record_status=success.status,
        reconciliation_status="passed" if reconcile.reconciliation_passed else "blocked",
        evidence_complete=evidence_complete,
        closeout_status=close.closeout_status,
        command_policy_status=command.command_policy_status,
        output_policy_status=output.output_policy_status,
        command_review_status=review.command_review_status,
        m063_authorization_status=auth.authorization_status,
        runbook_preview_status=runbook.preview_status,
        selected_future_command_set=auth.selected_future_command_set,
        selected_candidate=success.selected_candidate,
        selected_region=success.selected_region,
        historical_billable_action_performed=success.historical_billable_action_performed,
        report_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M062 is offline and performs no Lambda or SSH operation",
                    "M063 GPU visibility authorization is future-only",
                    *success.warnings,
                    *reconcile.warnings,
                    *close.warnings,
                    *command.warnings,
                    *output.warnings,
                    *review.warnings,
                    *auth.warnings,
                    *runbook.warnings,
                ]
            )
        ),
    )


def load_lambda_m062_report(path: str | Path) -> LambdaM062Report:
    return LambdaM062Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m062_report(path: str | Path, report: LambdaM062Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
