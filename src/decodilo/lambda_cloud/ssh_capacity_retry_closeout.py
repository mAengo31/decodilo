"""Close out SSH-connectivity retries blocked by Lambda capacity."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_error_closeout import (
    load_lambda_capacity_error_closeout,
)
from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report


class LambdaSSHCapacityRetryCloseoutReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M055D"
    selected_candidate: str | None = None
    selected_region: str | None = None
    launch_request_sent: bool
    launch_response_received: bool
    status_code: int | None = None
    provider_error_message_redacted: str | None = None
    classification: str | None = None
    owned_instance_id_present: bool
    ssh_attempted: bool
    stderr_capture_needed: bool
    termination_required: bool
    termination_attempted: bool
    final_instance_count: int
    final_unmanaged_count: int
    closeout_status: str
    closeout_succeeded: bool
    capacity_error_confirmed: bool
    teardown_review_status: str
    same_candidate_region_retry_blocked: bool
    future_ssh_retry_requires_new_candidate_or_fresh_availability: bool
    conservative_estimated_spend: float | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHCapacityRetryCloseoutReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("SSH capacity retry closeout cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_capacity_retry_closeout_from_paths(
    *,
    workdir: str | Path,
    capacity_closeout: str | Path,
    post_discovery: str | Path,
) -> LambdaSSHCapacityRetryCloseoutReport:
    workdir_path = Path(workdir)
    run_report = _load_json(workdir_path / "report.json")
    closeout = load_lambda_capacity_error_closeout(capacity_closeout)
    discovery = load_lambda_live_discovery_report(post_discovery)
    spend_audit = _try_load_json(workdir_path / "spend-audit.json")

    selected_candidate = (
        run_report.get("selected_candidate")
        or run_report.get("selected_shape")
        or closeout.selected_shape
    )
    selected_region = run_report.get("selected_region") or closeout.selected_region
    launch_received = bool(
        run_report.get("launch_response_received")
        or run_report.get("launch_response_http_status") is not None
        or closeout.status_code is not None
    )
    final_instance_count = len(discovery.instances)
    final_unmanaged_count = len(discovery.unmanaged_instances)
    blockers: list[str] = []
    if not bool(run_report.get("launch_request_sent")):
        blockers.append("launch_request_not_sent")
    if not closeout.capacity_error_confirmed:
        blockers.append("capacity_error_not_confirmed")
    if closeout.owned_instance_id_present or bool(run_report.get("owned_instance_id_redacted")):
        blockers.append("owned_instance_id_present")
    if final_instance_count != 0 or final_unmanaged_count != 0:
        blockers.append("post_discovery_found_visible_or_unmanaged_instances")
    ssh_attempted = bool(run_report.get("ssh_attempted"))
    if ssh_attempted:
        blockers.append("ssh_should_not_have_been_attempted_after_capacity_rejection")

    closeout_succeeded = not blockers and closeout.closeout_succeeded
    return LambdaSSHCapacityRetryCloseoutReport(
        selected_candidate=selected_candidate,
        selected_region=selected_region,
        launch_request_sent=bool(run_report.get("launch_request_sent")),
        launch_response_received=launch_received,
        status_code=run_report.get("launch_response_http_status") or closeout.status_code,
        provider_error_message_redacted=(
            run_report.get("launch_response_error_message_redacted")
            or closeout.provider_error_message_redacted
        ),
        classification=run_report.get("launch_response_classification")
        or closeout.classification,
        owned_instance_id_present=closeout.owned_instance_id_present
        or bool(run_report.get("owned_instance_id_redacted")),
        ssh_attempted=ssh_attempted,
        stderr_capture_needed=ssh_attempted,
        termination_required=(
            False if closeout.capacity_error_confirmed else closeout.termination_required
        ),
        termination_attempted=bool(
            run_report.get("termination_request_sent") or closeout.termination_attempted
        ),
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        closeout_status=(
            "closed_capacity_unavailable_no_instance_created"
            if closeout_succeeded
            else "unresolved"
        ),
        closeout_succeeded=closeout_succeeded,
        capacity_error_confirmed=closeout.capacity_error_confirmed,
        teardown_review_status=(
            "teardown_not_required_capacity_rejected"
            if closeout_succeeded
            else "manual_review_required"
        ),
        same_candidate_region_retry_blocked=closeout.capacity_error_confirmed,
        future_ssh_retry_requires_new_candidate_or_fresh_availability=(
            closeout.capacity_error_confirmed
        ),
        conservative_estimated_spend=_optional_float(spend_audit, "estimated_spend"),
        blockers=blockers,
        warnings=[
            "generic manual review is refined to no teardown required for capacity rejection",
            "same candidate/region retry remains blocked without fresh availability evidence",
        ],
    )


def load_lambda_ssh_capacity_retry_closeout(
    path: str | Path,
) -> LambdaSSHCapacityRetryCloseoutReport:
    return LambdaSSHCapacityRetryCloseoutReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_capacity_retry_closeout(
    path: str | Path,
    report: LambdaSSHCapacityRetryCloseoutReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _try_load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return _load_json(path)


def _optional_float(data: dict | None, key: str) -> float | None:
    if not data or data.get(key) is None:
        return None
    return float(data[key])
