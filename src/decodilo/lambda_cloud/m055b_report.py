"""M055B offline SSH failure diagnostic hardening report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    load_lambda_ssh_stderr_capture_policy,
)
from decodilo.lambda_cloud.ssh_host_key_policy import load_lambda_ssh_host_key_policy
from decodilo.lambda_cloud.ssh_identity_policy import load_lambda_ssh_identity_policy
from decodilo.lambda_cloud.ssh_private_key_file_policy import (
    load_lambda_ssh_private_key_file_policy,
)
from decodilo.lambda_cloud.ssh_probe_diagnostic_artifact import (
    load_lambda_ssh_probe_diagnostic,
)
from decodilo.lambda_cloud.ssh_probe_retry_policy import load_lambda_ssh_probe_retry_policy
from decodilo.lambda_cloud.ssh_provider_key_attachment_diagnostic import (
    load_lambda_ssh_provider_key_attachment_diagnostic,
)
from decodilo.lambda_cloud.ssh_username_policy import load_lambda_ssh_username_policy


class LambdaM055BReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M055B"
    report_passed: bool
    username_policy_status: str
    selected_username: str
    host_key_policy_status: str
    identity_policy_status: str
    private_key_file_policy_status: str
    stderr_capture_policy_status: str
    provider_key_attachment_diagnostic_status: str
    historical_probe_classification: str
    retry_policy_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM055BReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M055B report cannot enable launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M055B report cannot include blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m055b_report_from_paths(
    *,
    username_policy: str | Path,
    host_key_policy: str | Path,
    identity_policy: str | Path,
    private_key_file_policy: str | Path,
    stderr_policy: str | Path,
    provider_key_diagnostic: str | Path,
    probe_diagnostic: str | Path,
    retry_policy: str | Path,
) -> LambdaM055BReport:
    username = load_lambda_ssh_username_policy(username_policy)
    host_key = load_lambda_ssh_host_key_policy(host_key_policy)
    identity = load_lambda_ssh_identity_policy(identity_policy)
    private_key = load_lambda_ssh_private_key_file_policy(private_key_file_policy)
    stderr = load_lambda_ssh_stderr_capture_policy(stderr_policy)
    provider = load_lambda_ssh_provider_key_attachment_diagnostic(provider_key_diagnostic)
    probe = load_lambda_ssh_probe_diagnostic(probe_diagnostic)
    retry = load_lambda_ssh_probe_retry_policy(retry_policy)
    blockers = [
        *username.blockers,
        *host_key.blockers,
        *identity.blockers,
        *private_key.blockers,
        *stderr.blockers,
        *provider.blockers,
        *probe.blockers,
        *retry.blockers,
    ]
    warnings = [
        *username.warnings,
        *host_key.warnings,
        *identity.warnings,
        *private_key.warnings,
        *stderr.warnings,
        *provider.warnings,
        *probe.warnings,
        *retry.warnings,
    ]
    policy_statuses_ok = {
        username.username_policy_status,
        host_key.host_key_policy_status,
        identity.identity_policy_status,
        private_key.private_key_file_policy_status,
        stderr.capture_policy_status,
    } == {"policy_defined"}
    provider_ok = provider.key_attachment_diagnostic_status != "mismatch"
    report_passed = policy_statuses_ok and provider_ok and not blockers
    return LambdaM055BReport(
        report_passed=report_passed,
        username_policy_status=username.username_policy_status,
        selected_username=username.selected_username,
        host_key_policy_status=host_key.host_key_policy_status,
        identity_policy_status=identity.identity_policy_status,
        private_key_file_policy_status=private_key.private_key_file_policy_status,
        stderr_capture_policy_status=stderr.capture_policy_status,
        provider_key_attachment_diagnostic_status=(
            provider.key_attachment_diagnostic_status
        ),
        historical_probe_classification=probe.classification,
        retry_policy_status=retry.retry_policy_status,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def load_lambda_m055b_report(path: str | Path) -> LambdaM055BReport:
    return LambdaM055BReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m055b_report(path: str | Path, report: LambdaM055BReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
