"""M064 offline GPU visibility closeout and future M065 planning report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_closeout import (
    load_lambda_gpu_visibility_closeout,
)
from decodilo.lambda_cloud.gpu_visibility_evidence_package import (
    load_lambda_gpu_visibility_evidence_package,
)
from decodilo.lambda_cloud.gpu_visibility_parsed_output_audit import (
    load_lambda_gpu_visibility_parsed_output_audit,
)
from decodilo.lambda_cloud.gpu_visibility_reconciliation import (
    load_lambda_gpu_visibility_reconciliation,
)
from decodilo.lambda_cloud.gpu_visibility_success_record import (
    load_lambda_gpu_visibility_success_record,
)
from decodilo.lambda_cloud.m065_python_runtime_authorization import (
    load_lambda_m065_python_runtime_authorization,
)
from decodilo.lambda_cloud.m065_python_runtime_runbook_preview import (
    load_lambda_m065_python_runtime_runbook_preview,
)
from decodilo.lambda_cloud.python_runtime_command_policy import (
    load_lambda_python_runtime_command_policy,
)
from decodilo.lambda_cloud.python_runtime_command_review import (
    load_lambda_python_runtime_command_review,
)
from decodilo.lambda_cloud.python_runtime_output_policy import (
    load_lambda_python_runtime_output_policy,
)


class LambdaM064Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gpu_visibility_success_status: str
    parsed_output_audit_status: str
    reconciliation_status: str
    evidence_complete: bool
    closeout_status: str
    python_command_policy_status: str
    python_output_policy_status: str
    python_command_review_status: str
    m065_authorization_status: str
    runbook_preview_status: str
    selected_future_command_set: list[str] = Field(default_factory=list)
    parsed_gpu_name: str | None = None
    parsed_memory_total: str | None = None
    parsed_driver_version: str | None = None
    stdout_hash_prefix: str | None = None
    selected_candidate: str | None = None
    selected_region: str | None = None
    historical_billable_action_performed: bool
    m064_billable_action_performed: bool = False
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaM064Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.m064_billable_action_performed
        ):
            raise ValueError("M064 report cannot enable launch, mutation, or spend")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m064_report_from_paths(
    *,
    success_record: str | Path,
    parsed_output_audit: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    python_command_policy: str | Path,
    python_output_policy: str | Path,
    python_command_review: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM064Report:
    success = load_lambda_gpu_visibility_success_record(success_record)
    audit = load_lambda_gpu_visibility_parsed_output_audit(parsed_output_audit)
    reconcile = load_lambda_gpu_visibility_reconciliation(reconciliation)
    evidence_path = _infer_evidence_package_path(closeout)
    evidence = (
        load_lambda_gpu_visibility_evidence_package(evidence_path)
        if evidence_path.exists()
        else None
    )
    close = load_lambda_gpu_visibility_closeout(closeout)
    command = load_lambda_python_runtime_command_policy(python_command_policy)
    output = load_lambda_python_runtime_output_policy(python_output_policy)
    review = load_lambda_python_runtime_command_review(python_command_review)
    auth = load_lambda_m065_python_runtime_authorization(authorization)
    runbook = load_lambda_m065_python_runtime_runbook_preview(runbook_preview)
    blockers = [
        *success.blockers,
        *audit.blockers,
        *reconcile.errors,
        *close.blockers,
        *command.blockers,
        *output.blockers,
        *review.blockers,
        *auth.blockers,
        *runbook.blockers,
    ]
    evidence_complete = True if evidence is None else evidence.evidence_complete
    if success.status not in {
        "gpu_visibility_query_success",
        "gpu_visibility_query_executed_output_hash_only",
    }:
        blockers.append("gpu_visibility_success_record_not_success_or_hash_only")
    if audit.parsed_output_audit_status == "missing_output":
        blockers.append("gpu_visibility_output_missing")
    if not reconcile.reconciliation_passed:
        blockers.append("gpu_visibility_reconciliation_not_passed")
    if not evidence_complete:
        blockers.append("gpu_visibility_evidence_package_incomplete")
    if not close.closeout_succeeded:
        blockers.append("gpu_visibility_closeout_not_succeeded")
    if command.policy_status != "python_runtime_command_policy_defined_future_only":
        blockers.append("python_runtime_command_policy_not_ready")
    if output.output_policy_status != "python_runtime_output_policy_defined_future_only":
        blockers.append("python_runtime_output_policy_not_ready")
    if review.command_review_status != "python_runtime_command_review_passed_future_only":
        blockers.append("python_runtime_command_review_not_ready")
    if auth.authorization_status != "authorized_for_future_m065_python_version_query_review":
        blockers.append("m065_authorization_not_ready")
    if runbook.preview_status != "ready_for_future_m065_python_version_query_review":
        blockers.append("m065_runbook_preview_not_ready")
    warnings = [
        "M064 is offline and performs no Lambda, SSH, remote command, or credential operation",
        "M065 Python runtime authorization is future-only",
        *success.warnings,
        *audit.warnings,
        *reconcile.warnings,
        *close.warnings,
        *command.warnings,
        *output.warnings,
        *review.warnings,
        *auth.warnings,
        *runbook.warnings,
    ]
    if evidence is not None:
        warnings.extend(evidence.warnings)
    return LambdaM064Report(
        gpu_visibility_success_status=success.status,
        parsed_output_audit_status=audit.parsed_output_audit_status,
        reconciliation_status="passed" if reconcile.reconciliation_passed else "blocked",
        evidence_complete=evidence_complete,
        closeout_status=close.closeout_status,
        python_command_policy_status=command.policy_status,
        python_output_policy_status=output.output_policy_status,
        python_command_review_status=review.command_review_status,
        m065_authorization_status=auth.authorization_status,
        runbook_preview_status=runbook.preview_status,
        selected_future_command_set=auth.selected_future_command_set,
        parsed_gpu_name=success.parsed_gpu_name,
        parsed_memory_total=success.parsed_memory_total,
        parsed_driver_version=success.parsed_driver_version,
        stdout_hash_prefix=success.stdout_hash_prefix,
        selected_candidate=success.selected_candidate,
        selected_region=success.selected_region,
        historical_billable_action_performed=success.historical_billable_action_performed,
        report_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
    )


def _infer_evidence_package_path(closeout: str | Path) -> Path:
    path = Path(closeout)
    return path.with_name("gpu-visibility-evidence-package.json")


def load_lambda_m064_report(path: str | Path) -> LambdaM064Report:
    return LambdaM064Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m064_report(path: str | Path, report: LambdaM064Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
