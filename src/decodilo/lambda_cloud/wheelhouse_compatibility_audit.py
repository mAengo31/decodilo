"""Compatibility audit for M068W Linux/Python 3.10 wheelhouses."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.wheelhouse_manifest import load_lambda_wheelhouse_manifest


class LambdaWheelhouseCompatibilityAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M068W"
    compatibility_audit_passed: bool
    target_python: str
    target_platform: str
    target_abi: str
    audited_files: int
    compatibility_notes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_non_launching(self) -> LambdaWheelhouseCompatibilityAudit:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("wheelhouse compatibility audit must not enable launch or spend")
        if self.compatibility_audit_passed and self.blockers:
            raise ValueError("passing wheelhouse compatibility audit cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_lambda_wheelhouse_compatibility_from_paths(
    *,
    manifest: str | Path,
) -> LambdaWheelhouseCompatibilityAudit:
    man = load_lambda_wheelhouse_manifest(manifest)
    blockers = [*man.blockers]
    notes: list[str] = []
    if man.manifest_status != "manifest_built":
        blockers.append("wheelhouse_manifest_not_built")
    package_names = set(man.package_names)
    for required in ("pydantic", "pydantic-core"):
        if required not in package_names:
            blockers.append(f"required_package_missing:{required}")
    for file in man.package_files:
        platform_tag = file.platform_tag.lower()
        python_tag = file.python_tag.lower()
        abi_tag = file.abi_tag.lower()
        if file.filename.endswith((".tar.gz", ".zip")):
            blockers.append(f"source_distribution_not_allowed:{file.filename}")
        if "darwin" in platform_tag or "macosx" in platform_tag:
            blockers.append(f"macos_wheel_rejected:{file.filename}")
        if "cp313" in python_tag or "cp313" in abi_tag:
            blockers.append(f"python_313_abi_rejected:{file.filename}")
        if platform_tag == "any":
            if abi_tag != "none" or not (
                python_tag == "py3" or "py310" in python_tag or "cp310" in python_tag
            ):
                blockers.append(f"pure_python_wheel_not_py3_compatible:{file.filename}")
            notes.append(f"pure_python_wheel_accepted:{file.filename}")
            continue
        if not (
            "cp310" in python_tag
            and "cp310" in abi_tag
            and "manylinux" in platform_tag
            and "x86_64" in platform_tag
        ):
            blockers.append(f"wheel_not_manylinux_cp310_x86_64:{file.filename}")
        else:
            notes.append(f"manylinux_cp310_wheel_accepted:{file.filename}")
    return LambdaWheelhouseCompatibilityAudit(
        compatibility_audit_passed=not blockers,
        target_python=man.target_python,
        target_platform=man.target_platform,
        target_abi=man.target_abi,
        audited_files=len(man.package_files),
        compatibility_notes=sorted(set(notes)),
        blockers=sorted(set(blockers)),
        warnings=["compatibility audit is local-only and does not install packages"],
    )


def load_lambda_wheelhouse_compatibility_audit(
    path: str | Path,
) -> LambdaWheelhouseCompatibilityAudit:
    return LambdaWheelhouseCompatibilityAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_wheelhouse_compatibility_audit(
    path: str | Path,
    report: LambdaWheelhouseCompatibilityAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
