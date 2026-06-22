"""Offline diagnostic artifact for historical and future SSH probe failures."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_failure_classifier import (
    LambdaSSHFailureClassification,
    classify_ssh_failure,
)


class LambdaSSHProbeDiagnosticArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    stderr_capture_present: bool
    classification: LambdaSSHFailureClassification
    tcp_readiness_succeeded: bool | None = None
    ssh_exit_code: int | None = None
    likely_next_action: str
    host_discovery_status: str | None = None
    ssh_port_reachable: bool | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHProbeDiagnosticArtifact:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("SSH probe diagnostic cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_probe_diagnostic_from_paths(
    *,
    workdir: str | Path | None = None,
    fallback_report: str | Path | None = None,
) -> LambdaSSHProbeDiagnosticArtifact:
    report = _load_json(fallback_report) if fallback_report else {}
    evidence = _load_json(Path(workdir) / "ssh-connectivity-evidence.json") if workdir else {}
    stderr_redacted = evidence.get("stderr_redacted") or report.get("stderr_redacted")
    exit_code = evidence.get("exit_status") or evidence.get("ssh_exit_status")
    if exit_code is None and (report.get("ssh_auth_result") == "auth_failed"):
        exit_code = 255
    tcp_ready = (
        evidence.get("ssh_port_reachable")
        if "ssh_port_reachable" in evidence
        else report.get("ssh_port_reachable")
    )
    classified = classify_ssh_failure(
        exit_code=exit_code,
        stderr_redacted=stderr_redacted,
        tcp_readiness_succeeded=tcp_ready,
    )
    next_action = (
        "enable_redacted_stderr_capture"
        if classified.classification == "unknown_exit_255"
        else "review_classified_ssh_failure"
    )
    blockers = (
        ["stderr_capture_missing_for_exit_255"]
        if classified.classification == "unknown_exit_255"
        else []
    )
    return LambdaSSHProbeDiagnosticArtifact(
        stderr_capture_present=bool(stderr_redacted),
        classification=classified.classification,
        tcp_readiness_succeeded=tcp_ready,
        ssh_exit_code=exit_code,
        likely_next_action=next_action,
        host_discovery_status=report.get("host_discovery_status")
        or evidence.get("host_discovery_status"),
        ssh_port_reachable=tcp_ready,
        blockers=blockers,
        warnings=classified.warnings,
    )


def _load_json(path: str | Path | None) -> dict:
    if path is None:
        return {}
    target = Path(path)
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def load_lambda_ssh_probe_diagnostic(
    path: str | Path,
) -> LambdaSSHProbeDiagnosticArtifact:
    return LambdaSSHProbeDiagnosticArtifact.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_probe_diagnostic(
    path: str | Path,
    report: LambdaSSHProbeDiagnosticArtifact,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
