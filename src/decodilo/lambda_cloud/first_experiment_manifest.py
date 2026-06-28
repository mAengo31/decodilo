"""Future M071R first experiment manifest candidate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.first_experiment_command_discovery import (
    load_lambda_first_experiment_command_discovery,
)
from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    M067R_REMOTE_BUNDLE_PATH,
    M067R_REMOTE_EXTRACT_DIR,
    M067R_REMOTE_IMPORT_PROBE_PATH,
    M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
    M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
    M068R_REMOTE_RUNTIME_TARGET_DIR,
    LambdaRemoteVerticalSliceCommandEntry,
    render_lambda_remote_vertical_slice_argv,
)

LambdaFirstExperimentManifestStatus = Literal[
    "manifest_ready_for_future_review",
    "manifest_blocked",
]


class LambdaFirstExperimentManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_schema_version: int = 1
    milestone: str = "M071R"
    manifest_status: LambdaFirstExperimentManifestStatus
    command_entries: list[LambdaRemoteVerticalSliceCommandEntry] = Field(
        default_factory=list
    )
    source_bundle_path: str
    source_bundle_sha256: str | None = None
    dependency_bundle_path: str
    dependency_bundle_sha256: str | None = None
    stop_on_first_failure: bool = True
    max_remote_commands: int = 12
    dependency_strategy: str = "local_wheelhouse"
    no_internet_install: bool = True
    no_downloads: bool = True
    no_training: bool = True
    no_background: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_manifest(self) -> LambdaFirstExperimentManifest:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("first experiment manifest must be future-only")
        if len(self.command_entries) > self.max_remote_commands:
            raise ValueError("first experiment manifest exceeds max_remote_commands")
        if self.manifest_status == "manifest_ready_for_future_review" and self.blockers:
            raise ValueError("ready first experiment manifest cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_first_experiment_manifest_from_paths(
    *,
    command_discovery: str | Path,
    source_bundle: str | Path,
    dependency_bundle: str | Path,
) -> LambdaFirstExperimentManifest:
    discovery = load_lambda_first_experiment_command_discovery(command_discovery)
    source_path = Path(source_bundle)
    dependency_path = Path(dependency_bundle)
    blockers: list[str] = []
    if discovery.discovery_status != "safe_experiment_command_found":
        blockers.append("no_safe_experiment_command_found")
    if not source_path.exists():
        blockers.append("source_bundle_missing")
    if not dependency_path.exists():
        blockers.append("dependency_bundle_missing")
    entries: list[LambdaRemoteVerticalSliceCommandEntry] = []
    if not blockers:
        commands = [
            ("python_version_check", ["python3", "--version"]),
            ("source_bundle_hash_check", ["sha256sum", M067R_REMOTE_BUNDLE_PATH]),
            (
                "dependency_bundle_hash_check",
                ["sha256sum", M068R_REMOTE_DEPENDENCY_BUNDLE_PATH],
            ),
            ("source_extract_dir", ["mkdir", "-p", M067R_REMOTE_EXTRACT_DIR]),
            (
                "source_bundle_extract",
                ["tar", "-xzf", M067R_REMOTE_BUNDLE_PATH, "-C", M067R_REMOTE_EXTRACT_DIR],
            ),
            (
                "dependency_extract_dir",
                ["mkdir", "-p", M068R_REMOTE_DEPENDENCY_EXTRACT_DIR],
            ),
            (
                "dependency_bundle_extract",
                [
                    "tar",
                    "-xzf",
                    M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
                    "-C",
                    M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
                ],
            ),
            (
                "dependency_install_local_only",
                [
                    "python3",
                    "-m",
                    "pip",
                    "install",
                    "--no-index",
                    "--find-links",
                    M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
                    "--target",
                    M068R_REMOTE_RUNTIME_TARGET_DIR,
                    "pydantic",
                    "beautifulsoup4",
                    "numpy",
                ],
            ),
            (
                "decodilo_import_check",
                [
                    "env",
                    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
                    "python3",
                    M067R_REMOTE_IMPORT_PROBE_PATH,
                ],
            ),
            (
                "decodilo_cli_help_check",
                [
                    "env",
                    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
                    "python3",
                    "-m",
                    "decodilo.cli",
                    "--help",
                ],
            ),
            ("first_experiment_command", discovery.argv_tokens),
        ]
        entries = [
            LambdaRemoteVerticalSliceCommandEntry(
                stage=stage,
                argv_tokens=argv,
                exact_command=render_lambda_remote_vertical_slice_argv(argv),
                timeout_seconds=discovery.timeout_seconds or 30,
                failure_stage_if_nonzero=stage,
            )
            for stage, argv in commands
        ]
    return LambdaFirstExperimentManifest(
        manifest_status=(
            "manifest_ready_for_future_review" if not blockers else "manifest_blocked"
        ),
        command_entries=entries,
        max_remote_commands=len(entries) if entries else 12,
        source_bundle_path=str(source_path),
        source_bundle_sha256=_sha256_file(source_path) if source_path.exists() else None,
        dependency_bundle_path=str(dependency_path),
        dependency_bundle_sha256=(
            _sha256_file(dependency_path) if dependency_path.exists() else None
        ),
        blockers=blockers,
        warnings=["M071R manifest is non-executable until future one-shot authorization"],
    )


def load_lambda_first_experiment_manifest(path: str | Path) -> LambdaFirstExperimentManifest:
    return LambdaFirstExperimentManifest.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_first_experiment_manifest(
    path: str | Path,
    report: LambdaFirstExperimentManifest,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
