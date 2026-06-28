"""Offline SSH-readiness history for Lambda candidate/region pairs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

DEFAULT_SSH_READINESS_REPORTS = (
    Path("/tmp/decodilo-lambda-m057/report.json"),
    Path("/tmp/decodilo-lambda-m059/report.json"),
    Path("/tmp/decodilo-lambda-m061/report.json"),
    Path("/tmp/decodilo-lambda-m063/report.json"),
    Path("/tmp/decodilo-lambda-m065/report.json"),
    Path("/tmp/decodilo-lambda-m067r/report.json"),
)


class LambdaSSHReadinessRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    milestone: str
    selected_candidate: str | None
    selected_region: str | None
    launch_request_sent: bool
    running_verified: bool
    host_discovery_status: str | None = None
    ssh_port_reachable: bool
    ssh_attempted: bool
    ssh_auth_result: str | None = None
    remote_command_result: str | None = None
    termination_verified: bool
    ssh_ready_success: bool
    ssh_port_not_reachable: bool


class LambdaSSHReadinessPairSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    selected_candidate: str
    selected_region: str
    ssh_ready_success_count: int = 0
    ssh_port_not_reachable_count: int = 0
    attempts: int = 0
    latest_status: str


class LambdaSSHReadinessHistory(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    candidate_region_records: list[LambdaSSHReadinessRecord] = Field(default_factory=list)
    candidate_region_summaries: list[LambdaSSHReadinessPairSummary] = Field(
        default_factory=list
    )
    ssh_ready_success_count: int
    ssh_port_not_reachable_count: int
    last_successful_candidate_region: dict[str, str] | None = None
    preferred_known_good_candidate_region: dict[str, str] | None = None
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_offline_history(self) -> LambdaSSHReadinessHistory:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("SSH readiness history cannot enable launch, mutation, or spend")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_readiness_history(
    report_paths: list[str | Path] | None = None,
) -> LambdaSSHReadinessHistory:
    paths = [Path(p) for p in (report_paths or DEFAULT_SSH_READINESS_REPORTS)]
    records: list[LambdaSSHReadinessRecord] = []
    warnings: list[str] = [
        "M067S SSH readiness history is offline and reads completed run reports only",
    ]
    for path in paths:
        if not path.exists():
            warnings.append(f"missing_history_report:{path}")
            continue
        records.append(_record_from_report(path, _read_json(path)))

    summaries: dict[tuple[str, str], dict[str, Any]] = {}
    last_success: dict[str, str] | None = None
    for record in records:
        if not record.selected_candidate or not record.selected_region:
            continue
        key = (record.selected_candidate, record.selected_region)
        item = summaries.setdefault(
            key,
            {
                "selected_candidate": key[0],
                "selected_region": key[1],
                "ssh_ready_success_count": 0,
                "ssh_port_not_reachable_count": 0,
                "attempts": 0,
                "latest_status": "unknown",
            },
        )
        item["attempts"] += 1
        if record.ssh_ready_success:
            item["ssh_ready_success_count"] += 1
            item["latest_status"] = "ssh_ready_success"
            last_success = {"selected_candidate": key[0], "selected_region": key[1]}
        elif record.ssh_port_not_reachable:
            item["ssh_port_not_reachable_count"] += 1
            item["latest_status"] = "ssh_port_not_reachable"
    pair_summaries = [
        LambdaSSHReadinessPairSummary(**item)
        for item in sorted(
            summaries.values(),
            key=lambda value: (value["selected_candidate"], value["selected_region"]),
        )
    ]
    preferred = _preferred_known_good(pair_summaries, last_success)
    return LambdaSSHReadinessHistory(
        candidate_region_records=records,
        candidate_region_summaries=pair_summaries,
        ssh_ready_success_count=sum(1 for record in records if record.ssh_ready_success),
        ssh_port_not_reachable_count=sum(
            1 for record in records if record.ssh_port_not_reachable
        ),
        last_successful_candidate_region=last_success,
        preferred_known_good_candidate_region=preferred,
        warnings=warnings,
    )


def _record_from_report(path: Path, report: dict[str, Any]) -> LambdaSSHReadinessRecord:
    selected_candidate = report.get("selected_candidate") or report.get("selected_shape")
    selected_region = report.get("selected_region")
    ssh_ready_success = (
        bool(report.get("launch_request_sent"))
        and report.get("readonly_verify_running_result") == "running"
        and report.get("host_discovery_status") == "FOUND"
        and bool(report.get("ssh_port_reachable"))
        and bool(report.get("ssh_attempted"))
        and report.get("remote_command_result") == "succeeded"
        and bool(report.get("termination_verified"))
    )
    ssh_port_not_reachable = (
        report.get("vertical_slice_status") == "ssh_port_not_reachable"
        or report.get("ssh_auth_result") == "ssh_port_not_reachable"
        or "ssh_port_not_reachable" in report.get("errors", [])
    )
    return LambdaSSHReadinessRecord(
        milestone=_milestone_from_path(path, report),
        selected_candidate=selected_candidate,
        selected_region=selected_region,
        launch_request_sent=bool(report.get("launch_request_sent")),
        running_verified=report.get("readonly_verify_running_result") == "running",
        host_discovery_status=report.get("host_discovery_status"),
        ssh_port_reachable=bool(report.get("ssh_port_reachable")),
        ssh_attempted=bool(report.get("ssh_attempted")),
        ssh_auth_result=report.get("ssh_auth_result"),
        remote_command_result=report.get("remote_command_result"),
        termination_verified=bool(report.get("termination_verified")),
        ssh_ready_success=ssh_ready_success,
        ssh_port_not_reachable=ssh_port_not_reachable,
    )


def _preferred_known_good(
    summaries: list[LambdaSSHReadinessPairSummary],
    last_success: dict[str, str] | None,
) -> dict[str, str] | None:
    if last_success is None:
        return None
    good = [
        summary
        for summary in summaries
        if summary.ssh_ready_success_count > 0
        and summary.ssh_port_not_reachable_count == 0
    ]
    if not good:
        return last_success
    selected = sorted(
        good,
        key=lambda item: (
            -item.ssh_ready_success_count,
            item.selected_candidate != "gpu_1x_a10",
            item.selected_candidate,
            item.selected_region,
        ),
    )[0]
    return {
        "selected_candidate": selected.selected_candidate,
        "selected_region": selected.selected_region,
    }


def _milestone_from_path(path: Path, report: dict[str, Any]) -> str:
    run_id = str(report.get("run_id") or "")
    if run_id:
        return run_id.split("-")[1].upper() if "-" in run_id else run_id
    return path.parent.name.replace("decodilo-lambda-", "").upper()


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_lambda_ssh_readiness_history(path: str | Path) -> LambdaSSHReadinessHistory:
    return LambdaSSHReadinessHistory.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_readiness_history(
    path: str | Path,
    report: LambdaSSHReadinessHistory,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
