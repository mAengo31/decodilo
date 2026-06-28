"""Planning for a Linux/Python 3.10 Lambda dependency wheelhouse."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_dependency_bundle import (
    load_lambda_runtime_dependency_inventory,
)

M068W_MILESTONE = "M068W"
DEFAULT_TARGET_PYTHON = "3.10"
DEFAULT_TARGET_PLATFORM = "manylinux2014_x86_64"
DEFAULT_TARGET_IMPLEMENTATION = "cp"
DEFAULT_TARGET_ABI = "cp310"

PYDANTIC_RUNTIME_DEPENDENCIES = [
    "annotated-types",
    "pydantic",
    "pydantic-core",
    "typing-extensions",
    "typing-inspection",
]


class LambdaLinuxPython310WheelhousePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = M068W_MILESTONE
    plan_status: Literal["plan_built", "blocked"]
    target_python: str
    target_platform: str
    target_implementation: str = DEFAULT_TARGET_IMPLEMENTATION
    target_abi: str = DEFAULT_TARGET_ABI
    required_packages: list[str] = Field(default_factory=list)
    download_requirements: list[str] = Field(default_factory=list)
    excluded_dependency_groups: list[str] = Field(default_factory=list)
    excluded_artifact_classes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_non_launching(self) -> LambdaLinuxPython310WheelhousePlan:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M068W wheelhouse plan must not enable launch or spend")
        if self.plan_status == "plan_built" and self.blockers:
            raise ValueError("passing wheelhouse plan cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_linux_python310_wheelhouse_plan_from_paths(
    *,
    inventory: str | Path,
    target_python: str = DEFAULT_TARGET_PYTHON,
    target_platform: str = DEFAULT_TARGET_PLATFORM,
) -> LambdaLinuxPython310WheelhousePlan:
    inv = load_lambda_runtime_dependency_inventory(inventory)
    blockers = list(inv.blockers)
    if inv.inventory_status != "inventory_built":
        blockers.append("runtime_dependency_inventory_not_built")
    runtime_requirements = sorted(set(inv.runtime_dependencies))
    runtime_names = sorted(_requirement_name(req) for req in runtime_requirements)
    required = sorted(set(runtime_names + PYDANTIC_RUNTIME_DEPENDENCIES))
    if "pydantic" not in runtime_names:
        blockers.append("pydantic_missing_from_runtime_inventory")
    return LambdaLinuxPython310WheelhousePlan(
        plan_status="plan_built" if not blockers else "blocked",
        target_python=target_python,
        target_platform=target_platform,
        required_packages=required,
        download_requirements=runtime_requirements,
        excluded_dependency_groups=["dev", "test", "torch"],
        excluded_artifact_classes=[
            "source_distributions",
            "local_site_packages_copy",
            "macos_wheels",
            "python_313_abi",
            "private_key_material",
            ".env",
            "credential_files",
        ],
        blockers=sorted(set(blockers)),
        warnings=[
            "M068W is local-only: no Lambda, SSH, remote command, install, or spend",
            "future Lambda install must use the uploaded wheelhouse with --no-index",
        ],
    )


def load_lambda_linux_python310_wheelhouse_plan(
    path: str | Path,
) -> LambdaLinuxPython310WheelhousePlan:
    return LambdaLinuxPython310WheelhousePlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_linux_python310_wheelhouse_plan(
    path: str | Path,
    report: LambdaLinuxPython310WheelhousePlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _requirement_name(requirement: str) -> str:
    for marker in ("<", ">", "=", "!", "~", "[", ";", " "):
        requirement = requirement.split(marker, 1)[0]
    return requirement.strip().replace("_", "-").lower()
