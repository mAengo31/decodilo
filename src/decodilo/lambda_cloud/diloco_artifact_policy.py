"""DiLoCo artifact policy checks over the manifest-driven capture policy."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.diloco_artifact_parser import (
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
    load_lambda_remote_vslice_manifest_artifact_policy,
)


class LambdaDilocoArtifactPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M081S"
    policy_status: str
    declared_artifact_path: str | None
    diloco_declared_artifact_supported: bool
    manifest_driven: bool
    no_arbitrary_file_reads: bool
    reject_undeclared_paths: bool
    reject_directories: bool
    reject_globs: bool
    reject_fallback_paths: bool
    reject_relative_paths: bool
    reject_traversal: bool
    reject_symlink_escapes: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaDilocoArtifactPolicyReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("DiLoCo artifact policy report must remain offline")
        if self.policy_status == "policy_passed" and self.blockers:
            raise ValueError("passing DiLoCo artifact policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_diloco_artifact_policy_report_from_path(
    *,
    manifest_artifact_policy: str | Path,
) -> LambdaDilocoArtifactPolicyReport:
    policy = load_lambda_remote_vslice_manifest_artifact_policy(manifest_artifact_policy)
    blockers: list[str] = []
    if policy.policy_status != "manifest_artifact_policy_defined":
        blockers.extend(policy.blockers or ["manifest_artifact_policy_not_defined"])
    if policy.declared_artifact_path != DILOCO_SMOKE_DECLARED_ARTIFACT_PATH:
        blockers.append("diloco_declared_artifact_path_missing")
    if not policy.diloco_smoke_declared_artifact_supported:
        blockers.append("diloco_declared_artifact_not_supported")
    if not policy.accept_only_manifest_declared_paths:
        blockers.append("manifest_artifact_policy_not_manifest_driven")
    for attr, blocker in [
        ("no_arbitrary_file_reads", "manifest_artifact_policy_allows_arbitrary_reads"),
        ("reject_undeclared_paths", "manifest_artifact_policy_allows_undeclared_paths"),
        ("reject_directories", "manifest_artifact_policy_allows_directories"),
        ("reject_globs", "manifest_artifact_policy_allows_globs"),
        ("reject_fallback_paths", "manifest_artifact_policy_allows_fallback_paths"),
        ("reject_relative_paths", "manifest_artifact_policy_allows_relative_paths"),
        ("reject_traversal", "manifest_artifact_policy_allows_traversal"),
        ("reject_symlink_escapes", "manifest_artifact_policy_allows_symlink_escapes"),
    ]:
        if getattr(policy, attr) is not True:
            blockers.append(blocker)
    return LambdaDilocoArtifactPolicyReport(
        policy_status="policy_passed" if not blockers else "blocked",
        declared_artifact_path=policy.declared_artifact_path,
        diloco_declared_artifact_supported=policy.diloco_smoke_declared_artifact_supported,
        manifest_driven=policy.accept_only_manifest_declared_paths,
        no_arbitrary_file_reads=policy.no_arbitrary_file_reads,
        reject_undeclared_paths=policy.reject_undeclared_paths,
        reject_directories=policy.reject_directories,
        reject_globs=policy.reject_globs,
        reject_fallback_paths=policy.reject_fallback_paths,
        reject_relative_paths=policy.reject_relative_paths,
        reject_traversal=policy.reject_traversal,
        reject_symlink_escapes=policy.reject_symlink_escapes,
        blockers=sorted(set(blockers)),
        warnings=["DiLoCo artifact capture is allowed only for manifest-declared output"],
    )


def load_lambda_diloco_artifact_policy_report(
    path: str | Path,
) -> LambdaDilocoArtifactPolicyReport:
    return LambdaDilocoArtifactPolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_artifact_policy_report(
    path: str | Path,
    report: LambdaDilocoArtifactPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
