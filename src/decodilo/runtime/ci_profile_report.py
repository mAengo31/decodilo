"""Static CI profile report generation."""

from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.runtime.ci_profile_manifest import (
    CI_PROFILE_MARKERS,
    CiProfileManifest,
    build_ci_profile_manifest,
    classify_test_file,
)

QUICK_EXCLUDED_MARKERS = frozenset(
    {
        "slow",
        "soak",
        "perf",
        "integration",
        "lifecycle",
        "hardware_optional",
        "lambda_live",
        "lambda_real_mutation",
        "subprocess_heavy",
        "launch_history_heavy",
    }
)
MANUAL_MARKERS = frozenset({"lambda_live", "lambda_real_mutation", "cloud_manual"})
MIXED_PROFILE_MARKERS = frozenset(
    {
        "quick",
        "lambda_offline",
        "lambda_live",
        "lambda_real_mutation",
        "runtime_local",
        "subprocess_heavy",
        "integration",
        "lifecycle",
        "perf",
        "soak",
        "launch_history_heavy",
        "torch_optional",
        "hardware_optional",
    }
)


class CiProfileReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 2
    known_profiles: list[str]
    pytest_commands: dict[str, str]
    marker_expressions: dict[str, str]
    static_test_counts_by_marker: dict[str, int]
    quick_test_files: list[str]
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    unmarked_test_count: int = 0
    unmarked_test_files: list[str] = Field(default_factory=list)
    unmarked_test_nodeids: list[str] = Field(default_factory=list)
    unmarked_tests: list[str] = Field(default_factory=list)
    inferred_unit_files: list[str] = Field(default_factory=list)
    tests_by_profile: dict[str, list[str]] = Field(default_factory=dict)
    files_with_mixed_profiles: list[str] = Field(default_factory=list)
    suspected_marker_conflicts: list[str] = Field(default_factory=list)
    conflicting_profile_tests: list[str] = Field(default_factory=list)
    quick_profile_count: int = 0
    lambda_offline_count: int = 0
    runtime_local_count: int = 0
    launch_history_heavy_count: int = 0
    manual_profile_count: int = 0
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> CiProfileReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("CI profile report cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _extract_explicit_markers(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    explicit = set(re.findall(r"pytest\.mark\.([A-Za-z_][A-Za-z0-9_]*)", text))
    return explicit & set(CI_PROFILE_MARKERS)


def _collect_nodeids(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    try:
        module = ast.parse(source)
    except SyntaxError:
        return [str(path)]

    nodeids: list[str] = []
    for node in module.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
            "test_"
        ):
            nodeids.append(f"{path}::{node.name}")
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and (
                    child.name.startswith("test_")
                ):
                    nodeids.append(f"{path}::{node.name}::{child.name}")
    return nodeids or [str(path)]


def _classify_for_report(path: Path) -> tuple[set[str], bool]:
    markers = _extract_explicit_markers(path) | classify_test_file(path)
    if markers:
        return markers, False
    return {"unit"}, True


def build_ci_profile_report(
    *,
    tests_root: str | Path = "tests",
    manifest: CiProfileManifest | None = None,
) -> CiProfileReport:
    manifest = manifest or build_ci_profile_manifest()
    test_files = sorted(Path(tests_root).glob("test_*.py"))
    marker_counts: Counter[str] = Counter()
    tests_by_profile: defaultdict[str, list[str]] = defaultdict(list)
    unmarked_files: list[str] = []
    unmarked_nodeids: list[str] = []
    inferred_unit_files: list[str] = []
    conflicts: list[str] = []
    mixed_files: list[str] = []

    for path in test_files:
        markers, inferred_unit = _classify_for_report(path)
        nodeids = _collect_nodeids(path)
        if inferred_unit:
            inferred_unit_files.append(str(path))
        if not markers:
            unmarked_files.append(str(path))
            unmarked_nodeids.extend(nodeids)
            continue

        for marker in sorted(markers):
            marker_counts[marker] += 1
            tests_by_profile[marker].extend(nodeids)

        if "quick" in markers and markers & QUICK_EXCLUDED_MARKERS:
            conflicts.append(str(path))
        if "lambda_live" in markers and "lambda_offline" in markers:
            conflicts.append(str(path))
        if "lambda_real_mutation" in markers and "lambda_offline" in markers:
            conflicts.append(str(path))

        mixed = sorted(markers & MIXED_PROFILE_MARKERS)
        if len(mixed) > 1:
            mixed_files.append(f"{path}: {', '.join(mixed)}")

    warnings: list[str] = []
    recommendations: list[str] = []
    if unmarked_files:
        warnings.append(f"{len(unmarked_files)} tests have no static profile marker")
        recommendations.append("Add explicit pytestmark entries for unclassified tests.")
    if inferred_unit_files:
        recommendations.append(
            f"{len(inferred_unit_files)} local files were classified as unit by "
            "the conservative static fallback; add explicit pytestmark when editing them."
        )
    if conflicts:
        warnings.append(f"{len(conflicts)} tests have conflicting static profiles")
    quick_count = len(tests_by_profile.get("quick", []))
    if quick_count > 75:
        warnings.append(f"quick profile has {quick_count} tests, above the target of 75")
        recommendations.append("Remove non-representative tests from the quick profile.")

    sorted_tests_by_profile = {
        marker: sorted(nodeids) for marker, nodeids in sorted(tests_by_profile.items())
    }
    return CiProfileReport(
        known_profiles=[profile.name for profile in manifest.profiles],
        pytest_commands={
            profile.name: profile.pytest_command for profile in manifest.profiles
        },
        marker_expressions={
            profile.name: profile.marker_expression for profile in manifest.profiles
        },
        static_test_counts_by_marker=dict(sorted(marker_counts.items())),
        quick_test_files=manifest.quick_test_files,
        warnings=warnings,
        recommendations=recommendations,
        unmarked_test_count=len(unmarked_files),
        unmarked_test_files=unmarked_files,
        unmarked_test_nodeids=unmarked_nodeids,
        unmarked_tests=unmarked_files,
        inferred_unit_files=inferred_unit_files,
        tests_by_profile=sorted_tests_by_profile,
        files_with_mixed_profiles=sorted(mixed_files),
        suspected_marker_conflicts=sorted(conflicts),
        conflicting_profile_tests=sorted(conflicts),
        quick_profile_count=quick_count,
        lambda_offline_count=len(tests_by_profile.get("lambda_offline", [])),
        runtime_local_count=len(tests_by_profile.get("runtime_local", [])),
        launch_history_heavy_count=len(tests_by_profile.get("launch_history_heavy", [])),
        manual_profile_count=sum(
            len(tests_by_profile.get(marker, [])) for marker in MANUAL_MARKERS
        ),
    )


def write_ci_profile_report(path: str | Path, report: CiProfileReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_ci_profile_report(path: str | Path) -> CiProfileReport:
    return CiProfileReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
