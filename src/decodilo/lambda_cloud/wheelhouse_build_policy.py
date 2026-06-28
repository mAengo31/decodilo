"""Build policy for M068W wheelhouse preparation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.linux_python310_wheelhouse_plan import (
    load_lambda_linux_python310_wheelhouse_plan,
)
from decodilo.lambda_cloud.wheelhouse_candidate_audit import (
    load_lambda_wheelhouse_candidate_audit,
)


class LambdaWheelhouseBuildPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M068W"
    policy_status: Literal[
        "use_existing_compatible_wheelhouse",
        "blocked_needs_operator_approval_for_local_wheel_download",
        "approved_controlled_local_wheel_download",
        "blocked_no_safe_strategy",
    ]
    binary_wheels_only: bool = True
    no_source_distributions: bool = True
    no_build_from_source: bool = True
    no_local_install: bool = True
    no_lambda_side_internet: bool = True
    no_dev_test_dependencies: bool = True
    required_secret_scan: bool = True
    required_compatibility_audit: bool = True
    controlled_local_download_approved: bool = False
    download_command_preview: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaWheelhouseBuildPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("wheelhouse build policy must not enable launch or spend")
        if not (
            self.binary_wheels_only
            and self.no_source_distributions
            and self.no_build_from_source
            and self.no_local_install
            and self.no_lambda_side_internet
            and self.no_dev_test_dependencies
            and self.required_secret_scan
            and self.required_compatibility_audit
        ):
            raise ValueError("wheelhouse build policy weakens dependency safety")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_wheelhouse_build_policy_from_paths(
    *,
    plan: str | Path,
    existing_audit: str | Path,
    approve_controlled_local_wheel_download: bool = False,
) -> LambdaWheelhouseBuildPolicy:
    wheelhouse_plan = load_lambda_linux_python310_wheelhouse_plan(plan)
    audit = load_lambda_wheelhouse_candidate_audit(existing_audit)
    blockers = [*wheelhouse_plan.blockers]
    status: Literal[
        "use_existing_compatible_wheelhouse",
        "blocked_needs_operator_approval_for_local_wheel_download",
        "approved_controlled_local_wheel_download",
        "blocked_no_safe_strategy",
    ]
    if wheelhouse_plan.plan_status != "plan_built":
        blockers.append("wheelhouse_plan_not_built")
        status = "blocked_no_safe_strategy"
    elif audit.audit_status == "compatible_wheelhouse_found":
        status = "use_existing_compatible_wheelhouse"
    elif approve_controlled_local_wheel_download:
        status = "approved_controlled_local_wheel_download"
    else:
        blockers.append("operator_approval_for_controlled_local_wheel_download_required")
        status = "blocked_needs_operator_approval_for_local_wheel_download"
    command = [
        "python3",
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--implementation",
        wheelhouse_plan.target_implementation,
        "--python-version",
        wheelhouse_plan.target_python.replace(".", ""),
        "--abi",
        wheelhouse_plan.target_abi,
        "--platform",
        wheelhouse_plan.target_platform,
        "--dest",
        "/tmp/decodilo-wheelhouse-m068w",
        *wheelhouse_plan.download_requirements,
    ]
    return LambdaWheelhouseBuildPolicy(
        policy_status=status,
        controlled_local_download_approved=approve_controlled_local_wheel_download,
        download_command_preview=command,
        blockers=sorted(set(blockers)),
        warnings=[
            "M068W policy is local-only and does not authorize Lambda access",
            "download command is for dev machine wheel retrieval only, never Lambda",
        ],
    )


def load_lambda_wheelhouse_build_policy(path: str | Path) -> LambdaWheelhouseBuildPolicy:
    return LambdaWheelhouseBuildPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_wheelhouse_build_policy(
    path: str | Path,
    report: LambdaWheelhouseBuildPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
