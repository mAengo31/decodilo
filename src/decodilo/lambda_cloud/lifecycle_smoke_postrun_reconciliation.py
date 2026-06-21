"""Post-run reconciliation for the Lambda lifecycle smoke."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.m029_report import load_lambda_m029_report

_BILLABLE_STATES = {"booting", "pending", "running", "active", "stopping", "unknown"}


class LambdaLifecycleSmokePostrunReconciliation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    owned_instance_id_redacted: str | None = None
    owned_instance_final_state: str | None = None
    termination_verified: bool
    final_instance_count: int
    final_unmanaged_count: int
    billable_state_remaining_count: int
    unmanaged_billable_count: int
    reconciliation_passed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_read_only(self) -> LambdaLifecycleSmokePostrunReconciliation:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("post-run reconciliation cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lifecycle_smoke_postrun_reconciliation_from_paths(
    *,
    workdir: str | Path,
    post_discovery: str | Path,
) -> LambdaLifecycleSmokePostrunReconciliation:
    workdir_path = Path(workdir)
    report = load_lambda_m029_report(workdir_path / "report.json")
    discovery = load_lambda_live_discovery_report(post_discovery)
    errors: list[str] = []
    if not (workdir_path / "ledger.json").exists():
        errors.append("ledger_missing")
    if not (workdir_path / "journal.jsonl").exists():
        errors.append("journal_missing")
    billable_remaining = sum(
        1 for instance in discovery.instances if instance.status in _BILLABLE_STATES
    )
    unmanaged_billable = sum(
        1
        for instance in discovery.instances
        if instance.status in _BILLABLE_STATES
        and instance.instance_id in set(discovery.unmanaged_instances)
    )
    if not report.termination_verified:
        errors.append("termination_not_verified")
    if len(discovery.instances) != 0:
        errors.append("final_discovery_visible_instances_present")
    if len(discovery.unmanaged_instances) != 0:
        errors.append("final_discovery_unmanaged_instances_present")
    if billable_remaining:
        errors.append("billable_state_remaining")
    return LambdaLifecycleSmokePostrunReconciliation(
        owned_instance_id_redacted=report.owned_instance_id_redacted,
        owned_instance_final_state=report.readonly_verify_terminated_result,
        termination_verified=report.termination_verified,
        final_instance_count=len(discovery.instances),
        final_unmanaged_count=len(discovery.unmanaged_instances),
        billable_state_remaining_count=billable_remaining,
        unmanaged_billable_count=unmanaged_billable,
        reconciliation_passed=not errors,
        warnings=["post-run reconciliation is read-only"],
        errors=sorted(set(errors)),
    )


def load_lambda_lifecycle_smoke_postrun_reconciliation(
    path: str | Path,
) -> LambdaLifecycleSmokePostrunReconciliation:
    return LambdaLifecycleSmokePostrunReconciliation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lifecycle_smoke_postrun_reconciliation(
    path: str | Path,
    report: LambdaLifecycleSmokePostrunReconciliation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
