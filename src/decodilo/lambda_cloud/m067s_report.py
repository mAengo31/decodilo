"""M067S offline closeout and retry-selection report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_vertical_slice_closeout import (
    load_lambda_remote_vertical_slice_closeout,
)
from decodilo.lambda_cloud.remote_vertical_slice_reconciliation import (
    load_lambda_remote_vertical_slice_reconciliation,
)
from decodilo.lambda_cloud.remote_vslice_candidate_selector import (
    load_lambda_remote_vslice_candidate_selection,
)
from decodilo.lambda_cloud.remote_vslice_retry_authorization import (
    load_lambda_remote_vslice_retry_authorization,
)
from decodilo.lambda_cloud.remote_vslice_retry_decision import (
    load_lambda_remote_vslice_retry_decision,
)
from decodilo.lambda_cloud.ssh_proven_candidate_policy import (
    load_lambda_ssh_proven_candidate_policy,
)
from decodilo.lambda_cloud.ssh_readiness_history import (
    load_lambda_ssh_readiness_history,
)


class LambdaM067SReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    closeout_status: str
    reconciliation_passed: bool
    ssh_ready_success_count: int
    ssh_port_not_reachable_count: int
    excluded_candidate_regions: list[dict[str, str | int]] = Field(default_factory=list)
    preferred_known_good_candidate_region: dict[str, str] | None = None
    candidate_selection_status: str | None = None
    retry_decision_status: str
    authorization_status: str
    report_passed: bool
    decodilo_not_tested: bool
    m067s_billable_action_performed: bool = False
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_offline_report(self) -> LambdaM067SReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.m067s_billable_action_performed
        ):
            raise ValueError("M067S report cannot enable launch, mutation, or spend")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m067s_report_from_paths(
    *,
    closeout: str | Path,
    reconciliation: str | Path,
    ssh_readiness_history: str | Path,
    candidate_policy: str | Path,
    retry_decision: str | Path,
    authorization: str | Path,
    candidate_selection: str | Path | None = None,
) -> LambdaM067SReport:
    close = load_lambda_remote_vertical_slice_closeout(closeout)
    reconcile = load_lambda_remote_vertical_slice_reconciliation(reconciliation)
    history = load_lambda_ssh_readiness_history(ssh_readiness_history)
    policy = load_lambda_ssh_proven_candidate_policy(candidate_policy)
    decision = load_lambda_remote_vslice_retry_decision(retry_decision)
    auth = load_lambda_remote_vslice_retry_authorization(authorization)
    selection = (
        load_lambda_remote_vslice_candidate_selection(candidate_selection)
        if candidate_selection is not None
        else None
    )
    blockers = [
        *close.blockers,
        *reconcile.errors,
    ]
    if close.closeout_status != "closed_pre_manifest_ssh_port_not_reachable":
        blockers.append("m067r_not_closed_as_pre_manifest_ssh_port_failure")
    if not reconcile.reconciliation_passed:
        blockers.append("m067r_reconciliation_not_passed")
    if not close.decodilo_not_tested:
        blockers.append("decodilo_should_not_be_classified_as_tested")
    warnings = [
        "M067S is offline: no Lambda, SSH, upload, remote command, credential, or spend",
        "M067R was a pre-manifest SSH/TCP readiness failure, not a Decodilo failure",
        *close.warnings,
        *reconcile.warnings,
        *history.warnings,
        *policy.warnings,
        *decision.warnings,
        *auth.warnings,
    ]
    if decision.blockers:
        warnings.append(
            "retry decision blockers are future-launch blockers, not M067S closeout blockers"
        )
        warnings.extend(f"future_retry_blocker:{item}" for item in decision.blockers)
    if auth.blockers:
        warnings.append(
            "authorization blockers are expected when M067S chooses wait/no immediate retry"
        )
        warnings.extend(f"future_authorization_blocker:{item}" for item in auth.blockers)
    if selection is not None:
        warnings.extend(selection.warnings)
    return LambdaM067SReport(
        closeout_status=close.closeout_status,
        reconciliation_passed=reconcile.reconciliation_passed,
        ssh_ready_success_count=history.ssh_ready_success_count,
        ssh_port_not_reachable_count=history.ssh_port_not_reachable_count,
        excluded_candidate_regions=policy.excluded_candidate_regions,
        preferred_known_good_candidate_region=policy.preferred_known_good_candidate_region,
        candidate_selection_status=selection.selection_status if selection else None,
        retry_decision_status=decision.decision_status,
        authorization_status=auth.authorization_status,
        report_passed=not blockers,
        decodilo_not_tested=close.decodilo_not_tested,
        historical_billable_action_performed=close.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
    )


def load_lambda_m067s_report(path: str | Path) -> LambdaM067SReport:
    return LambdaM067SReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m067s_report(path: str | Path, report: LambdaM067SReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
