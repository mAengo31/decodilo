"""Offline SSH-proven candidate history update for proven remote smoke runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHProvenCandidateHistoryUpdateStatus = Literal[
    "ssh_proven_candidate_history_updated",
    "ssh_proven_candidate_history_not_updated",
]

PROVEN_CAPABILITIES = {
    "launch": "launch_request_sent",
    "host_discovery": "host_discovery_found",
    "tcp_22_readiness": "ssh_port_reachable",
    "ssh_banner_readiness": "ssh_banner_ready",
    "source_upload": "source_bundle_upload_succeeded",
    "dependency_upload": "dependency_bundle_upload_succeeded",
    "local_only_dependency_install": "local_dependency_install_succeeded",
    "decodilo_command_execution": "remote_command_succeeded",
    "artifact_capture": "experiment_output_artifact_capture_succeeded",
    "owned_instance_termination_verification": "termination_verified",
}


class LambdaSSHProvenCandidateHistoryUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M084"
    update_status: LambdaSSHProvenCandidateHistoryUpdateStatus
    candidate_region_records: list[dict[str, Any]] = Field(default_factory=list)
    candidate_region_summaries: list[dict[str, Any]] = Field(default_factory=list)
    proven_candidate_regions: list[dict[str, Any]] = Field(default_factory=list)
    gpu_1x_a10_us_west_1_recorded: bool
    gpu_1x_a10_us_east_1_preserved: bool
    unrelated_regions_not_marked_proven: bool
    prior_history_preserved: bool
    last_successful_candidate_region: dict[str, str] | None = None
    preferred_known_good_candidate_regions: list[dict[str, str]] = Field(
        default_factory=list
    )
    ssh_ready_success_count: int
    ssh_port_not_reachable_count: int
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_update(self) -> LambdaSSHProvenCandidateHistoryUpdate:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M084 SSH history update must remain offline")
        if self.update_status == "ssh_proven_candidate_history_updated" and self.blockers:
            raise ValueError("updated SSH history cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_proven_candidate_history_update_from_paths(
    *,
    prior_history: str | Path,
    workdir: str | Path,
) -> LambdaSSHProvenCandidateHistoryUpdate:
    prior_path = Path(prior_history)
    workdir_path = Path(workdir)
    prior = _read_json(prior_path) if prior_path.exists() else {}
    report = _read_json(workdir_path / "report.json")
    evidence_path = workdir_path / "remote-vslice-evidence.json"
    evidence = _read_json(evidence_path) if evidence_path.exists() else {}
    candidate = report.get("selected_shape") or report.get("selected_candidate")
    region = report.get("selected_region")
    milestone = _infer_milestone(workdir_path, report)
    proven_for = {
        "launch": bool(report.get("launch_request_sent")),
        "host_discovery": report.get("host_discovery_status") == "FOUND",
        "tcp_22_readiness": bool(report.get("ssh_port_reachable")),
        "ssh_banner_readiness": bool(evidence.get("ssh_banner_ready")),
        "source_upload": bool(report.get("source_bundle_upload_succeeded")),
        "dependency_upload": bool(report.get("dependency_bundle_upload_succeeded")),
        "local_only_dependency_install": bool(
            report.get("local_dependency_install_succeeded")
        ),
        "decodilo_command_execution": report.get("remote_command_result") == "succeeded",
        "artifact_capture": bool(
            report.get("experiment_output_artifact_capture_succeeded")
        ),
        "owned_instance_termination_verification": bool(
            report.get("termination_verified")
        ),
    }
    all_proven = all(proven_for.values())
    latest_record = {
        "milestone": milestone,
        "selected_candidate": candidate,
        "selected_region": region,
        "launch_request_sent": bool(report.get("launch_request_sent")),
        "running_verified": report.get("readonly_verify_running_result") == "running",
        "host_discovery_status": report.get("host_discovery_status"),
        "ssh_port_reachable": bool(report.get("ssh_port_reachable")),
        "ssh_banner_ready": bool(evidence.get("ssh_banner_ready")),
        "ssh_banner_prefix_observed": bool(evidence.get("ssh_banner_prefix_observed")),
        "source_upload_passed": proven_for["source_upload"],
        "dependency_upload_passed": proven_for["dependency_upload"],
        "local_only_dependency_install_passed": proven_for[
            "local_only_dependency_install"
        ],
        "remote_command_result": report.get("remote_command_result"),
        "artifact_capture_passed": proven_for["artifact_capture"],
        "termination_verified": proven_for["owned_instance_termination_verification"],
        "ssh_ready_success": all_proven,
        "ssh_port_not_reachable": False,
        "proven_for": proven_for,
    }
    records = [
        dict(record)
        for record in prior.get("candidate_region_records", [])
        if isinstance(record, dict)
    ]
    records = [
        record
        for record in records
        if not (
            record.get("milestone") == milestone
            and record.get("selected_candidate") == candidate
            and record.get("selected_region") == region
        )
    ]
    records.append(latest_record)
    summaries = _summaries(records)
    proven_regions = _proven_regions(records)
    east_preserved = any(
        item.get("selected_candidate") == "gpu_1x_a10"
        and item.get("selected_region") == "us-east-1"
        and int(item.get("ssh_ready_success_count", 0)) > 0
        for item in summaries
    )
    west_recorded = any(
        item.get("selected_candidate") == "gpu_1x_a10"
        and item.get("selected_region") == "us-west-1"
        and int(item.get("ssh_ready_success_count", 0)) > 0
        for item in summaries
    )
    unrelated_proven = [
        item
        for item in proven_regions
        if (
            item.get("selected_candidate"),
            item.get("selected_region"),
        )
        not in {
            ("gpu_1x_a10", "us-east-1"),
            ("gpu_1x_a10", "us-west-1"),
        }
    ]
    blockers: list[str] = []
    if candidate != "gpu_1x_a10" or region != "us-west-1":
        blockers.append("candidate_region_unexpected")
    if not all_proven:
        blockers.append(f"{milestone.lower()}_not_fully_ssh_proven")
    if not east_preserved:
        blockers.append("prior_us_east_1_history_not_preserved")
    if unrelated_proven:
        blockers.append("unrelated_region_marked_proven")
    if not west_recorded:
        blockers.append("us_west_1_not_recorded")
    return LambdaSSHProvenCandidateHistoryUpdate(
        milestone=(
            "M088"
            if milestone == "M087R"
            else "M086"
            if milestone == "M085R"
            else "M084"
        ),
        update_status=(
            "ssh_proven_candidate_history_updated"
            if not blockers
            else "ssh_proven_candidate_history_not_updated"
        ),
        candidate_region_records=records,
        candidate_region_summaries=summaries,
        proven_candidate_regions=proven_regions,
        gpu_1x_a10_us_west_1_recorded=west_recorded,
        gpu_1x_a10_us_east_1_preserved=east_preserved,
        unrelated_regions_not_marked_proven=not unrelated_proven,
        prior_history_preserved=bool(records[:-1]),
        last_successful_candidate_region={
            "selected_candidate": "gpu_1x_a10",
            "selected_region": "us-west-1",
        }
        if west_recorded
        else prior.get("last_successful_candidate_region"),
        preferred_known_good_candidate_regions=[
            {
                "selected_candidate": item["selected_candidate"],
                "selected_region": item["selected_region"],
            }
            for item in proven_regions
        ],
        ssh_ready_success_count=sum(
            int(item.get("ssh_ready_success_count", 0)) for item in summaries
        ),
        ssh_port_not_reachable_count=sum(
            int(item.get("ssh_port_not_reachable_count", 0)) for item in summaries
        ),
        blockers=blockers,
        warnings=[
            "SSH readiness history update reads persisted reports only",
            f"only gpu_1x_a10/us-west-1 is newly marked proven by {milestone}",
        ],
    )


def _infer_milestone(workdir: Path, report: dict[str, Any]) -> str:
    name = workdir.name.lower()
    artifact_path = str(report.get("experiment_output_artifact_path") or "")
    if "m087r" in name or "parameter-fragment-smoke" in artifact_path:
        return "M087R"
    if "m085r" in name or "integrated-diloco-smoke" in artifact_path:
        return "M085R"
    if "m083r" in name or "diloco-optimizer-smoke" in artifact_path:
        return "M083R"
    return str(report.get("milestone") or report.get("run_id") or "unknown")


def load_lambda_ssh_proven_candidate_history_update(
    path: str | Path,
) -> LambdaSSHProvenCandidateHistoryUpdate:
    return LambdaSSHProvenCandidateHistoryUpdate.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_proven_candidate_history_update(
    path: str | Path,
    report: LambdaSSHProvenCandidateHistoryUpdate,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _summaries(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        candidate = record.get("selected_candidate")
        region = record.get("selected_region")
        if not candidate or not region:
            continue
        item = summaries.setdefault(
            (candidate, region),
            {
                "selected_candidate": candidate,
                "selected_region": region,
                "ssh_ready_success_count": 0,
                "ssh_port_not_reachable_count": 0,
                "attempts": 0,
                "latest_status": "unknown",
            },
        )
        item["attempts"] += 1
        if record.get("ssh_ready_success"):
            item["ssh_ready_success_count"] += 1
            item["latest_status"] = "ssh_ready_success"
        elif record.get("ssh_port_not_reachable"):
            item["ssh_port_not_reachable_count"] += 1
            item["latest_status"] = "ssh_port_not_reachable"
    return sorted(
        summaries.values(),
        key=lambda item: (item["selected_candidate"], item["selected_region"]),
    )


def _proven_regions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    proven: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        if not record.get("ssh_ready_success"):
            continue
        candidate = record.get("selected_candidate")
        region = record.get("selected_region")
        if not candidate or not region:
            continue
        capabilities = record.get("proven_for")
        if not isinstance(capabilities, dict):
            capabilities = {
                "launch": bool(record.get("launch_request_sent")),
                "host_discovery": record.get("host_discovery_status") == "FOUND",
                "tcp_22_readiness": bool(record.get("ssh_port_reachable")),
                "ssh_banner_readiness": bool(record.get("ssh_attempted")),
                "source_upload": False,
                "dependency_upload": False,
                "local_only_dependency_install": False,
                "decodilo_command_execution": bool(
                    record.get("remote_command_result") == "succeeded"
                ),
                "artifact_capture": False,
                "owned_instance_termination_verification": bool(
                    record.get("termination_verified")
                ),
            }
        proven[(candidate, region)] = {
            "selected_candidate": candidate,
            "selected_region": region,
            "proven_for": capabilities,
        }
    return sorted(
        proven.values(),
        key=lambda item: (item["selected_candidate"], item["selected_region"]),
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
