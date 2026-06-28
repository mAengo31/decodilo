"""M068W offline wheelhouse preparation report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.linux_python310_wheelhouse_plan import (
    load_lambda_linux_python310_wheelhouse_plan,
)
from decodilo.lambda_cloud.remote_dependency_bundle import (
    load_lambda_dependency_bundle_validation,
)
from decodilo.lambda_cloud.wheelhouse_build_policy import load_lambda_wheelhouse_build_policy
from decodilo.lambda_cloud.wheelhouse_candidate_audit import (
    load_lambda_wheelhouse_candidate_audit,
)
from decodilo.lambda_cloud.wheelhouse_compatibility_audit import (
    load_lambda_wheelhouse_compatibility_audit,
)
from decodilo.lambda_cloud.wheelhouse_manifest import load_lambda_wheelhouse_manifest
from decodilo.lambda_cloud.wheelhouse_secret_scan import load_lambda_wheelhouse_secret_scan


class LambdaM068WReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M068W"
    wheelhouse_status: str
    dependency_bundle_status: str
    download_used: bool
    internet_download_used: bool
    lambda_side_internet_required: bool = False
    m068r_retry_ready: bool
    bundle_path: str | None = None
    bundle_sha256: str | None = None
    package_names: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_non_launching(self) -> LambdaM068WReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.lambda_side_internet_required
        ):
            raise ValueError("M068W report must not enable launch, spend, or Lambda internet")
        if self.m068r_retry_ready and self.blockers:
            raise ValueError("M068W retry-ready report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m068w_report_from_paths(
    *,
    plan: str | Path,
    existing_audit: str | Path,
    build_policy: str | Path,
    wheelhouse_manifest: str | Path,
    secret_scan: str | Path,
    compatibility_audit: str | Path,
    bundle_validation: str | Path,
) -> LambdaM068WReport:
    wheel_plan = load_lambda_linux_python310_wheelhouse_plan(plan)
    audit = load_lambda_wheelhouse_candidate_audit(existing_audit)
    policy = load_lambda_wheelhouse_build_policy(build_policy)
    manifest = load_lambda_wheelhouse_manifest(wheelhouse_manifest)
    scan = load_lambda_wheelhouse_secret_scan(secret_scan)
    compat = load_lambda_wheelhouse_compatibility_audit(compatibility_audit)
    bundle = load_lambda_dependency_bundle_validation(bundle_validation)
    audit_blockers = (
        []
        if policy.policy_status == "approved_controlled_local_wheel_download"
        else audit.blockers
    )
    blockers = [
        *wheel_plan.blockers,
        *audit_blockers,
        *policy.blockers,
        *manifest.blockers,
        *scan.blockers,
        *compat.blockers,
        *bundle.blockers,
    ]
    ready = (
        manifest.manifest_status == "manifest_built"
        and scan.secret_scan_passed
        and compat.compatibility_audit_passed
        and bundle.validation_passed
        and not blockers
    )
    return LambdaM068WReport(
        wheelhouse_status=manifest.manifest_status,
        dependency_bundle_status="validated" if bundle.validation_passed else "blocked",
        download_used=manifest.download_used,
        internet_download_used=manifest.internet_download_used,
        m068r_retry_ready=ready,
        bundle_path=bundle.bundle_path,
        bundle_sha256=bundle.bundle_sha256,
        package_names=manifest.package_names,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M068W performed no Lambda, SSH, upload, remote command, or spend",
                    "future Lambda run must install only from uploaded local bundle",
                    *wheel_plan.warnings,
                    *audit.warnings,
                    *policy.warnings,
                    *manifest.warnings,
                    *scan.warnings,
                    *compat.warnings,
                    *bundle.warnings,
                ]
            )
        ),
    )


def load_lambda_m068w_report(path: str | Path) -> LambdaM068WReport:
    return LambdaM068WReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m068w_report(path: str | Path, report: LambdaM068WReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
