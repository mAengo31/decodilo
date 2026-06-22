"""M055 host-discovery fix report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m054b_closeout import LambdaM054BCloseoutReport

M055Status = Literal["offline_fix_ready", "real_run_success", "real_run_blocked"]


class LambdaM055Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M055"
    report_status: M055Status
    m054b_closeout_status: str
    lifecycle_launch_attempted: bool
    launch_response_status: int | None = None
    owned_instance_id_redacted: str | None = None
    running_verified: bool
    host_discovery_attempted: bool
    host_discovery_status: str | None = None
    host_discovery_source: str | None = None
    host_discovery_poll_count: int = 0
    host_discovery_duration_seconds: float = 0.0
    ssh_host_present: bool
    ssh_key_present: bool | None = None
    ssh_probe_attempted: bool
    ssh_auth_result: str | None = None
    ssh_port_readiness_attempted: bool = False
    ssh_port_reachable: bool | None = None
    ssh_port_poll_count: int = 0
    ssh_port_wait_seconds: float = 0.0
    ssh_port_connect_timeout_seconds: float | None = None
    remote_command_attempted: bool
    remote_command_result: str | None = None
    termination_request_sent: bool
    termination_verified: bool
    unmanaged_instance_count_post_run: int = 0
    mutating_operations: int = 0
    billable_action_performed: bool = False
    estimated_spend: float = 0.0
    conservative_spend_audit: float | None = None
    manual_review_required: bool
    launch_ready: bool = False
    launch_allowed: bool = False
    blocker: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    secret_scan_result: str = "not_run"
    remaining_blockers: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _disabled_flags(self) -> LambdaM055Report:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M055 report cannot enable launch flags")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m055_report(
    *,
    closeout: LambdaM054BCloseoutReport,
    run_report: dict | None = None,
    ssh_evidence: dict | None = None,
    spend_audit: dict | None = None,
    secret_scan_result: str = "not_run",
) -> LambdaM055Report:
    run_report = run_report or {}
    ssh_evidence = ssh_evidence or {}
    spend_audit = spend_audit or {}
    host_status = run_report.get("host_discovery_status") or ssh_evidence.get(
        "host_discovery_status"
    )
    ssh_ok = bool(ssh_evidence.get("probe_passed"))
    lifecycle_ok = bool(
        closeout.lifecycle_launch_succeeded
        and closeout.lifecycle_terminate_succeeded
    )
    manual_review = not (
        lifecycle_ok
        and host_status == "FOUND"
        and ssh_ok
        and bool(run_report.get("termination_verified"))
        and int(run_report.get("unmanaged_instance_count_post_run") or 0) == 0
        and secret_scan_result in {"clean", "NO_SECRET_PATTERN_MATCHES"}
    )
    blocker = _first(
        ssh_evidence.get("blockers"),
        run_report.get("errors"),
        closeout.blockers,
    )
    status: M055Status = (
        "real_run_success"
        if bool(run_report.get("launch_request_sent")) and not manual_review
        else "real_run_blocked"
        if bool(run_report.get("launch_request_sent"))
        else "offline_fix_ready"
    )
    return LambdaM055Report(
        report_status=status,
        m054b_closeout_status=closeout.closeout_status,
        lifecycle_launch_attempted=bool(run_report.get("launch_request_sent")),
        launch_response_status=run_report.get("launch_response_http_status"),
        owned_instance_id_redacted=run_report.get("owned_instance_id_redacted"),
        running_verified=run_report.get("readonly_verify_running_result") == "running",
        host_discovery_attempted=bool(
            run_report.get("host_discovery_attempted")
            or ssh_evidence.get("host_discovery_attempted")
        ),
        host_discovery_status=host_status,
        host_discovery_source=run_report.get("host_discovery_source")
        or ssh_evidence.get("host_discovery_source_path"),
        host_discovery_poll_count=int(
            run_report.get("host_discovery_poll_count")
            or ssh_evidence.get("host_discovery_poll_count")
            or 0
        ),
        host_discovery_duration_seconds=float(
            run_report.get("host_discovery_duration_seconds")
            or ssh_evidence.get("host_discovery_duration_seconds")
            or 0.0
        ),
        ssh_host_present=bool(run_report.get("ssh_host_present")),
        ssh_key_present=run_report.get("ssh_key_present"),
        ssh_probe_attempted=bool(
            run_report.get("ssh_attempted") or ssh_evidence.get("probe_attempted")
        ),
        ssh_auth_result=run_report.get("ssh_auth_result") or ssh_evidence.get("auth_result"),
        ssh_port_readiness_attempted=bool(
            run_report.get("ssh_port_readiness_attempted")
            or ssh_evidence.get("ssh_port_readiness_attempted")
        ),
        ssh_port_reachable=(
            run_report.get("ssh_port_reachable")
            if "ssh_port_reachable" in run_report
            else ssh_evidence.get("ssh_port_reachable")
        ),
        ssh_port_poll_count=int(
            run_report.get("ssh_port_poll_count")
            or ssh_evidence.get("ssh_port_poll_count")
            or 0
        ),
        ssh_port_wait_seconds=float(
            run_report.get("ssh_port_wait_seconds")
            or ssh_evidence.get("ssh_port_wait_seconds")
            or 0.0
        ),
        ssh_port_connect_timeout_seconds=(
            run_report.get("ssh_port_connect_timeout_seconds")
            if "ssh_port_connect_timeout_seconds" in run_report
            else ssh_evidence.get("ssh_port_connect_timeout_seconds")
        ),
        remote_command_attempted=bool(run_report.get("remote_command_attempted")),
        remote_command_result=run_report.get("remote_command_result"),
        termination_request_sent=bool(run_report.get("termination_request_sent")),
        termination_verified=bool(run_report.get("termination_verified")),
        unmanaged_instance_count_post_run=int(
            run_report.get("unmanaged_instance_count_post_run") or 0
        ),
        mutating_operations=int(run_report.get("mutating_operations") or 0),
        billable_action_performed=bool(run_report.get("billable_action_performed")),
        estimated_spend=float(run_report.get("estimated_spend") or 0.0),
        conservative_spend_audit=spend_audit.get("estimated_spend"),
        manual_review_required=manual_review,
        blocker=blocker,
        reason_codes=list(ssh_evidence.get("blockers") or []),
        secret_scan_result=secret_scan_result,
        remaining_blockers=[] if not manual_review else [blocker or "manual_review_required"],
        recommendations=[
            "run real M055 only with explicit billable confirmation",
            "inspect provider get/list metadata if host discovery remains blocked",
            "use LAMBDA_SSH_HOST_OVERRIDE only as an explicit operator fallback",
        ],
    )


def build_lambda_m055_report_from_paths(
    *,
    closeout: str | Path,
    workdir: str | Path | None = None,
    secret_scan_result: str = "not_run",
) -> LambdaM055Report:
    closeout_report = LambdaM054BCloseoutReport.model_validate_json(
        Path(closeout).read_text(encoding="utf-8")
    )
    run_report = _try_load_json(Path(workdir) / "report.json") if workdir else None
    ssh_evidence = (
        _try_load_json(Path(workdir) / "ssh-connectivity-evidence.json") if workdir else None
    )
    spend_audit = _try_load_json(Path(workdir) / "spend-audit.json") if workdir else None
    return build_lambda_m055_report(
        closeout=closeout_report,
        run_report=run_report,
        ssh_evidence=ssh_evidence,
        spend_audit=spend_audit,
        secret_scan_result=secret_scan_result,
    )


def write_lambda_m055_report(path: str | Path, report: LambdaM055Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _try_load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _first(*items) -> str | None:
    for item in items:
        if isinstance(item, list) and item:
            return str(item[0])
        if isinstance(item, str) and item:
            return item
    return None
