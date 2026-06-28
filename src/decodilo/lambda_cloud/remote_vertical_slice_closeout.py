"""Offline closeout for M067R remote vertical-slice attempts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaRemoteVerticalSliceCloseoutStatus = Literal[
    "closed_pre_manifest_ssh_port_not_reachable",
    "closed_vertical_slice_success",
    "closed_vertical_slice_failed_at_stage",
    "unresolved",
]


class LambdaRemoteVerticalSliceCloseout(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    closeout_status: LambdaRemoteVerticalSliceCloseoutStatus
    launch_request_sent: bool
    owned_instance_id_present: bool
    running_verification: str | None = None
    host_discovery: str | None = None
    tcp_22_readiness: bool
    ssh_attempted: bool
    source_bundle_upload_attempted: bool
    manifest_started: bool
    failed_before_manifest: bool
    failed_stage: str | None = None
    termination_verified: bool
    final_instance_count: int | None = None
    final_unmanaged_count: int | None = None
    teardown_clean: bool
    decodilo_not_tested: bool
    source_bundle_not_tested: bool
    package_install_attempted: bool
    download_attempted: bool
    training_attempted: bool
    historical_billable_action_performed: bool
    m067s_billable_action_performed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_offline_closeout(self) -> LambdaRemoteVerticalSliceCloseout:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.m067s_billable_action_performed
        ):
            raise ValueError("M067S closeout cannot enable launch, mutation, or spend")
        if self.closeout_status == "closed_pre_manifest_ssh_port_not_reachable":
            if (
                not self.launch_request_sent
                or not self.owned_instance_id_present
                or self.tcp_22_readiness
                or self.ssh_attempted
                or self.source_bundle_upload_attempted
                or self.manifest_started
                or not self.failed_before_manifest
                or self.failed_stage != "ssh_port_not_reachable"
                or not self.termination_verified
                or not self.teardown_clean
                or not self.decodilo_not_tested
            ):
                raise ValueError("pre-manifest SSH port closeout has inconsistent fields")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_vertical_slice_closeout_from_paths(
    *,
    workdir: str | Path,
    evidence: str | Path,
    post_discovery: str | Path,
) -> LambdaRemoteVerticalSliceCloseout:
    report = _read_json(Path(workdir) / "report.json")
    evidence_report = _read_json(evidence)
    post = _read_json(post_discovery)

    launch_request_sent = bool(report.get("launch_request_sent"))
    owned_instance_id_present = bool(report.get("owned_instance_id_redacted"))
    host_discovery = report.get("host_discovery_status") or evidence_report.get(
        "host_discovery_status"
    )
    tcp_22_readiness = bool(report.get("ssh_port_reachable"))
    ssh_attempted = bool(report.get("ssh_attempted"))
    source_bundle_upload_attempted = bool(report.get("source_bundle_upload_attempted"))
    manifest_started = bool(report.get("remote_command_attempted")) or bool(
        report.get("remote_command_stage_results")
    )
    termination_verified = bool(report.get("termination_verified"))
    final_instance_count = _int_or_none(post.get("instance_count"))
    final_unmanaged_count = _int_or_none(post.get("unmanaged_count"))
    teardown_clean = (
        termination_verified
        and final_instance_count == 0
        and final_unmanaged_count == 0
        and not bool(post.get("manual_review_required"))
    )
    vertical_status = report.get("vertical_slice_status")
    failed_before_manifest = (
        vertical_status == "ssh_port_not_reachable"
        and not ssh_attempted
        and not source_bundle_upload_attempted
        and not manifest_started
    )
    decodilo_not_tested = not source_bundle_upload_attempted and not manifest_started
    blockers: list[str] = []
    if not launch_request_sent:
        blockers.append("launch_request_not_sent")
    if not owned_instance_id_present:
        blockers.append("owned_instance_id_missing")
    if not termination_verified:
        blockers.append("termination_not_verified")
    if not teardown_clean:
        blockers.append("teardown_not_clean")
    if bool(report.get("package_install_attempted")):
        blockers.append("package_install_attempted")
    if bool(report.get("training_attempted")):
        blockers.append("training_attempted")

    if failed_before_manifest and teardown_clean:
        status: LambdaRemoteVerticalSliceCloseoutStatus = (
            "closed_pre_manifest_ssh_port_not_reachable"
        )
        failed_stage = "ssh_port_not_reachable"
    elif report.get("vertical_slice_status") == "vertical_slice_success" and teardown_clean:
        status = "closed_vertical_slice_success"
        failed_stage = None
    elif manifest_started and teardown_clean:
        status = "closed_vertical_slice_failed_at_stage"
        failed_stage = report.get("failed_stage")
    else:
        status = "unresolved"

    return LambdaRemoteVerticalSliceCloseout(
        closeout_status=status,
        launch_request_sent=launch_request_sent,
        owned_instance_id_present=owned_instance_id_present,
        running_verification=report.get("readonly_verify_running_result"),
        host_discovery=host_discovery,
        tcp_22_readiness=tcp_22_readiness,
        ssh_attempted=ssh_attempted,
        source_bundle_upload_attempted=source_bundle_upload_attempted,
        manifest_started=manifest_started,
        failed_before_manifest=failed_before_manifest,
        failed_stage=failed_stage,
        termination_verified=termination_verified,
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        teardown_clean=teardown_clean,
        decodilo_not_tested=decodilo_not_tested,
        source_bundle_not_tested=not source_bundle_upload_attempted,
        package_install_attempted=bool(report.get("package_install_attempted")),
        download_attempted=bool(report.get("download_attempted", False)),
        training_attempted=bool(report.get("training_attempted")),
        historical_billable_action_performed=bool(report.get("billable_action_performed")),
        blockers=sorted(set(blockers)) if status == "unresolved" else [],
        warnings=[
            "M067S is offline and performs no Lambda, SSH, upload, or remote command",
            "M067R stopped before Decodilo import, CLI, source-bundle, or manifest testing",
        ],
    )


def load_lambda_remote_vertical_slice_closeout(
    path: str | Path,
) -> LambdaRemoteVerticalSliceCloseout:
    return LambdaRemoteVerticalSliceCloseout.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vertical_slice_closeout(
    path: str | Path,
    report: LambdaRemoteVerticalSliceCloseout,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None
