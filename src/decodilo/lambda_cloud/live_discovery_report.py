"""Reports for Lambda live read-only discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.api_models import (
    LambdaFilesystem,
    LambdaImage,
    LambdaInstance,
    LambdaInstanceType,
    LambdaQuota,
    LambdaRegion,
    LambdaSSHKey,
    LambdaUsageEstimate,
)
from decodilo.lambda_cloud.endpoint_calibration import LambdaEndpointResult
from decodilo.lambda_cloud.live_discovery_redaction import LambdaRedactionMode
from decodilo.lambda_cloud.live_endpoint_coverage import LambdaEndpointCoverageReport
from decodilo.lambda_cloud.read_only_audit import LambdaReadOnlyAuditEntry


class LambdaLiveDiscoveryConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    base_url: str
    live_read_only: bool
    fail_on_partial: bool = False
    endpoint_set: Literal["minimal", "standard", "extended"] = "standard"
    max_pages: int = Field(default=10, gt=0)
    max_items: int = Field(default=1000, gt=0)
    redaction_mode: LambdaRedactionMode = "local_private_report"


class LambdaLiveDiscoverySummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    read_operations: int
    mutating_operations: int = 0
    unmanaged_instances: int
    endpoint_count_attempted: int = 0
    endpoint_count_succeeded: int = 0
    endpoint_count_failed: int = 0
    endpoint_count_failed_required: int = 0
    endpoint_count_failed_optional: int = 0
    endpoint_count_unsupported_optional: int = 0
    required_endpoint_success: bool = True
    optional_endpoint_warnings: list[str] = Field(default_factory=list)
    billable_action_performed: bool = False


class LambdaLiveDiscoveryReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    created_at_utc: str | None = None
    source: Literal["live_read_only", "fake_transport"] = "live_read_only"
    live_api_used: bool
    read_only_mode: bool = True
    mutation_guard_enabled: bool = True
    endpoint_policy_enabled: bool = True
    regions: list[LambdaRegion] = Field(default_factory=list)
    instance_types: list[LambdaInstanceType] = Field(default_factory=list)
    images: list[LambdaImage] = Field(default_factory=list)
    ssh_keys: list[LambdaSSHKey] = Field(default_factory=list)
    filesystems: list[LambdaFilesystem] = Field(default_factory=list)
    instances: list[LambdaInstance] = Field(default_factory=list)
    quota: LambdaQuota | None = None
    usage_estimate: LambdaUsageEstimate | None = None
    unmanaged_instances: list[str] = Field(default_factory=list)
    endpoint_set: Literal["minimal", "standard", "extended"] = "standard"
    endpoint_results: list[LambdaEndpointResult] = Field(default_factory=list)
    endpoint_coverage: LambdaEndpointCoverageReport | None = None
    endpoint_count_attempted: int = 0
    endpoint_count_succeeded: int = 0
    endpoint_count_failed: int = 0
    endpoint_count_failed_required: int = 0
    endpoint_count_failed_optional: int = 0
    endpoint_count_unsupported_optional: int = 0
    required_endpoint_success: bool = True
    optional_endpoint_warnings: list[str] = Field(default_factory=list)
    pagination_observed: bool = False
    redaction_mode: LambdaRedactionMode = "local_private_report"
    secret_source: Literal["api_key_file", "env_file"] | None = None
    secret_loaded: bool = False
    env_file_basename: str | None = None
    env_key: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    audit_log: list[LambdaReadOnlyAuditEntry] = Field(default_factory=list)
    secret_redacted: bool = True
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @property
    def summary(self) -> LambdaLiveDiscoverySummary:
        return LambdaLiveDiscoverySummary(
            read_operations=len(self.audit_log),
            mutating_operations=sum(1 for entry in self.audit_log if entry.mutation),
            unmanaged_instances=len(self.unmanaged_instances),
            endpoint_count_attempted=self.endpoint_count_attempted,
            endpoint_count_succeeded=self.endpoint_count_succeeded,
            endpoint_count_failed=self.endpoint_count_failed,
            endpoint_count_failed_required=self.endpoint_count_failed_required,
            endpoint_count_failed_optional=self.endpoint_count_failed_optional,
            endpoint_count_unsupported_optional=self.endpoint_count_unsupported_optional,
            required_endpoint_success=self.required_endpoint_success,
            optional_endpoint_warnings=self.optional_endpoint_warnings,
            billable_action_performed=self.billable_action_performed,
        )

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def load_lambda_live_discovery_report(path: str | Path) -> LambdaLiveDiscoveryReport:
    return LambdaLiveDiscoveryReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_live_discovery_report(
    path: str | Path,
    report: LambdaLiveDiscoveryReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
