"""Attest that M051B did not perform SSH or remote execution."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m029_report import load_lambda_m029_report


class LambdaNoRemoteExecutionAttestation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    ssh_key_attached_for_launch_payload: bool
    ssh_attempted: bool = False
    remote_command_attempted: bool = False
    package_install_attempted: bool = False
    training_attempted: bool = False
    setup_script_attempted: bool = False
    cloud_init_attempted: bool = False
    evidence_sources: list[str] = Field(default_factory=list)
    attestation_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaNoRemoteExecutionAttestation:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("no-remote attestation cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_no_remote_execution_attestation_from_paths(
    *,
    workdir: str | Path,
) -> LambdaNoRemoteExecutionAttestation:
    workdir_path = Path(workdir)
    report = load_lambda_m029_report(workdir_path / "report.json")
    blockers: list[str] = []
    if report.ssh_attempted:
        blockers.append("ssh_attempted")
    if report.remote_command_attempted:
        blockers.append("remote_command_attempted")
    if report.package_install_attempted:
        blockers.append("package_install_attempted")
    if report.training_attempted:
        blockers.append("training_attempted")
    return LambdaNoRemoteExecutionAttestation(
        ssh_key_attached_for_launch_payload=bool(report.selected_ssh_key_hash),
        ssh_attempted=report.ssh_attempted,
        remote_command_attempted=report.remote_command_attempted,
        package_install_attempted=report.package_install_attempted,
        training_attempted=report.training_attempted,
        setup_script_attempted=False,
        cloud_init_attempted=False,
        evidence_sources=[
            str(workdir_path / "report.json"),
            str(workdir_path / "journal.jsonl"),
        ],
        attestation_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=[
            "SSH key attachment for provider payload is not SSH use",
            "M052 attestation is based on persisted M051B run artifacts",
        ],
    )


def load_lambda_no_remote_execution_attestation(
    path: str | Path,
) -> LambdaNoRemoteExecutionAttestation:
    return LambdaNoRemoteExecutionAttestation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_no_remote_execution_attestation(
    path: str | Path,
    report: LambdaNoRemoteExecutionAttestation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
