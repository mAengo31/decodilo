"""Audit local wheelhouse candidates for M068W."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.linux_python310_wheelhouse_plan import (
    LambdaLinuxPython310WheelhousePlan,
    load_lambda_linux_python310_wheelhouse_plan,
)


class LambdaWheelhouseCandidate(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    filename: str
    package_name: str | None = None
    version: str | None = None
    python_tag: str | None = None
    abi_tag: str | None = None
    platform_tag: str | None = None
    candidate_status: Literal["compatible", "incompatible", "source_distribution"]
    blockers: list[str] = Field(default_factory=list)


class LambdaWheelhouseCandidateAudit(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M068W"
    audit_status: Literal["compatible_wheelhouse_found", "not_found", "blocked"]
    search_paths: list[str] = Field(default_factory=list)
    compatible_wheels: list[LambdaWheelhouseCandidate] = Field(default_factory=list)
    incompatible_wheels: list[LambdaWheelhouseCandidate] = Field(default_factory=list)
    source_distributions: list[LambdaWheelhouseCandidate] = Field(default_factory=list)
    missing_packages: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_non_launching(self) -> LambdaWheelhouseCandidateAudit:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("wheelhouse candidate audit must not enable launch or spend")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_existing_lambda_wheelhouse_candidates_from_paths(
    *,
    plan: str | Path,
    search_paths: list[str | Path],
) -> LambdaWheelhouseCandidateAudit:
    wheelhouse_plan = load_lambda_linux_python310_wheelhouse_plan(plan)
    candidates: list[LambdaWheelhouseCandidate] = []
    sdists: list[LambdaWheelhouseCandidate] = []
    for base in search_paths:
        base_path = Path(base)
        if not base_path.exists():
            continue
        for path in sorted(base_path.rglob("*")):
            if path.suffix == ".whl":
                candidates.append(_audit_wheel(path, wheelhouse_plan))
            elif path.suffixes[-2:] in ([".tar", ".gz"], [".tar", ".bz2"]) or path.suffix == ".zip":
                sdists.append(
                    LambdaWheelhouseCandidate(
                        path=str(path),
                        filename=path.name,
                        candidate_status="source_distribution",
                        blockers=["source_distribution_not_allowed"],
                    )
                )
    compatible = [
        candidate for candidate in candidates if candidate.candidate_status == "compatible"
    ]
    incompatible = [
        candidate for candidate in candidates if candidate.candidate_status == "incompatible"
    ]
    covered = {candidate.package_name for candidate in compatible if candidate.package_name}
    missing = sorted(
        package for package in wheelhouse_plan.required_packages if package not in covered
    )
    blockers = []
    if wheelhouse_plan.plan_status != "plan_built":
        blockers.append("wheelhouse_plan_not_built")
    if missing:
        blockers.extend(f"missing_package:{package}" for package in missing)
    status: Literal["compatible_wheelhouse_found", "not_found", "blocked"]
    if blockers:
        status = "not_found"
    else:
        status = "compatible_wheelhouse_found"
    return LambdaWheelhouseCandidateAudit(
        audit_status=status,
        search_paths=[str(Path(path)) for path in search_paths],
        compatible_wheels=compatible,
        incompatible_wheels=incompatible,
        source_distributions=sdists,
        missing_packages=missing,
        blockers=sorted(set(blockers)),
        warnings=[
            "existing wheelhouse audit is local-only and does not download or install packages"
        ],
    )


def load_lambda_wheelhouse_candidate_audit(path: str | Path) -> LambdaWheelhouseCandidateAudit:
    return LambdaWheelhouseCandidateAudit.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_wheelhouse_candidate_audit(
    path: str | Path,
    report: LambdaWheelhouseCandidateAudit,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _audit_wheel(path: Path, plan: LambdaLinuxPython310WheelhousePlan) -> LambdaWheelhouseCandidate:
    parsed = _parse_wheel_filename(path.name)
    blockers: list[str] = []
    if parsed is None:
        blockers.append("wheel_filename_unparseable")
        return LambdaWheelhouseCandidate(
            path=str(path),
            filename=path.name,
            candidate_status="incompatible",
            blockers=blockers,
        )
    package, version, python_tag, abi_tag, platform_tag = parsed
    normalized = package.replace("_", "-").lower()
    if "darwin" in platform_tag or "macosx" in platform_tag:
        blockers.append("macos_wheel_rejected")
    if "cp313" in python_tag or "cp313" in abi_tag:
        blockers.append("python_313_abi_rejected")
    if platform_tag == "any":
        if abi_tag != "none" or not (
            python_tag == "py3" or "py310" in python_tag or "cp310" in python_tag
        ):
            blockers.append("pure_python_wheel_not_py3_compatible")
    elif not (
        "cp310" in python_tag
        and "cp310" in abi_tag
        and "manylinux" in platform_tag
        and "x86_64" in platform_tag
    ):
        blockers.append("wheel_not_manylinux_cp310_x86_64")
    if normalized not in plan.required_packages:
        blockers.append(f"package_not_required:{normalized}")
    return LambdaWheelhouseCandidate(
        path=str(path),
        filename=path.name,
        package_name=normalized,
        version=version,
        python_tag=python_tag,
        abi_tag=abi_tag,
        platform_tag=platform_tag,
        candidate_status="compatible" if not blockers else "incompatible",
        blockers=sorted(set(blockers)),
    )


def _parse_wheel_filename(filename: str) -> tuple[str, str, str, str, str] | None:
    if not filename.endswith(".whl"):
        return None
    stem = filename[:-4]
    parts = stem.split("-")
    if len(parts) < 5:
        return None
    python_tag, abi_tag, platform_tag = parts[-3:]
    version = parts[1]
    package = parts[0]
    return package, version, python_tag, abi_tag, platform_tag
