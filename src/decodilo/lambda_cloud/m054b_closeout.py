"""Offline closeout for the M054B SSH-connectivity attempt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

M054BCloseoutStatus = Literal[
    "lifecycle_successful_ssh_host_discovery_blocked",
    "ssh_connectivity_success",
    "unresolved",
]


class LambdaM054BCloseoutReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M054B"
    closeout_status: M054BCloseoutStatus
    lifecycle_launch_succeeded: bool
    lifecycle_terminate_succeeded: bool
    ssh_connectivity_succeeded: bool
    ssh_probe_attempted: bool
    ssh_blocker: str | None = None
    root_cause_hypothesis: str
    issue_is_host_discovery_not_key_authentication: bool
    remote_command_attempted: bool
    file_transfer_attempted: bool
    port_forwarding_attempted: bool
    package_install_attempted: bool
    training_attempted: bool
    final_instance_count: int
    final_unmanaged_count: int
    teardown_verified_clean: bool
    next_milestone: str = "M055 host discovery fix"
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _disabled_flags(self) -> LambdaM054BCloseoutReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M054B closeout cannot enable launch or spend")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m054b_closeout(
    *,
    run_report: dict,
    ssh_evidence: dict,
    post_discovery: dict,
) -> LambdaM054BCloseoutReport:
    final_instances = _count_instances(post_discovery)
    final_unmanaged = int(
        _nested_get(post_discovery, "summary", "unmanaged_count")
        or post_discovery.get("unmanaged_count")
        or 0
    )
    launch_ok = bool(
        run_report.get("launch_request_sent")
        and run_report.get("launch_response_received")
        and run_report.get("launch_response_http_status") == 200
        and run_report.get("readonly_verify_running_result") == "running"
    )
    terminate_ok = bool(
        run_report.get("termination_request_sent")
        and run_report.get("termination_response_received")
        and run_report.get("termination_verified")
        and final_instances == 0
        and final_unmanaged == 0
    )
    ssh_ok = bool(ssh_evidence.get("probe_passed"))
    probe_attempted = bool(ssh_evidence.get("probe_attempted"))
    blocker = None
    blockers = list(ssh_evidence.get("blockers") or [])
    if blockers:
        blocker = str(blockers[0])
    if (
        launch_ok
        and terminate_ok
        and not ssh_ok
        and blocker == "ssh_host_not_present_in_provider_metadata"
    ):
        status: M054BCloseoutStatus = "lifecycle_successful_ssh_host_discovery_blocked"
    elif launch_ok and terminate_ok and ssh_ok:
        status = "ssh_connectivity_success"
    else:
        status = "unresolved"
    return LambdaM054BCloseoutReport(
        closeout_status=status,
        lifecycle_launch_succeeded=launch_ok,
        lifecycle_terminate_succeeded=terminate_ok,
        ssh_connectivity_succeeded=ssh_ok,
        ssh_probe_attempted=probe_attempted,
        ssh_blocker=blocker,
        root_cause_hypothesis=(
            "provider list/get metadata did not expose an SSH host/IP before the probe"
        ),
        issue_is_host_discovery_not_key_authentication=(
            not probe_attempted and blocker == "ssh_host_not_present_in_provider_metadata"
        ),
        remote_command_attempted=bool(run_report.get("remote_command_attempted")),
        file_transfer_attempted=bool(run_report.get("file_transfer_attempted")),
        port_forwarding_attempted=bool(run_report.get("port_forwarding_attempted")),
        package_install_attempted=bool(run_report.get("package_install_attempted")),
        training_attempted=bool(run_report.get("training_attempted")),
        final_instance_count=final_instances,
        final_unmanaged_count=final_unmanaged,
        teardown_verified_clean=terminate_ok,
        blockers=[] if status != "unresolved" else blockers or ["m054b_closeout_unresolved"],
        warnings=[
            "M054B is lifecycle-successful but must not be reported as SSH-successful"
        ]
        if status == "lifecycle_successful_ssh_host_discovery_blocked"
        else [],
    )


def build_lambda_m054b_closeout_from_paths(
    *,
    workdir: str | Path,
    post_discovery: str | Path,
) -> LambdaM054BCloseoutReport:
    base = Path(workdir)
    return build_lambda_m054b_closeout(
        run_report=_load_json(base / "report.json"),
        ssh_evidence=_load_json(base / "ssh-connectivity-evidence.json"),
        post_discovery=_load_json(post_discovery),
    )


def write_lambda_m054b_closeout(path: str | Path, report: LambdaM054BCloseoutReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _count_instances(discovery: dict) -> int:
    value = _nested_get(discovery, "summary", "instance_count")
    if value is not None:
        return int(value)
    if "instance_count" in discovery:
        return int(discovery["instance_count"])
    if isinstance(discovery.get("instances"), list):
        return len(discovery["instances"])
    return 0


def _nested_get(data: dict, *keys: str):
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
