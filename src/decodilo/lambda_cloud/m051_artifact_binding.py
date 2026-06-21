"""Hash binding for M051 one-shot execution artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m051_exact_command_binding import (
    load_lambda_m051_exact_command_binding,
)
from decodilo.lambda_cloud.m051_one_shot_arming import (
    load_lambda_m051_one_shot_arming,
)


class LambdaM051ArtifactBinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    binding_passed: bool
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    command_hash: str | None = None
    arming_hash: str | None = None
    command_binding_hash: str | None = None
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM051ArtifactBinding:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M051 artifact binding cannot enable launch")
        if self.binding_passed and (
            self.blockers or self.missing_items or self.hash_mismatches
        ):
            raise ValueError("M051 artifact binding cannot pass with binding errors")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_artifact_binding_from_paths(
    *,
    arming: str | Path,
    command_binding: str | Path,
) -> LambdaM051ArtifactBinding:
    arming_report = load_lambda_m051_one_shot_arming(arming)
    command_report = load_lambda_m051_exact_command_binding(command_binding)
    artifact_hashes = dict(arming_report.artifact_hashes)
    artifact_paths = dict(arming_report.artifact_paths)
    missing: list[str] = []
    mismatches: list[str] = []
    for name, expected in sorted(artifact_hashes.items()):
        path_text = artifact_paths.get(name)
        if not path_text:
            missing.append(name)
            continue
        path = Path(path_text)
        if not path.exists():
            missing.append(name)
            continue
        actual = _sha256_file(path)
        if actual != expected:
            mismatches.append(name)
    blockers: list[str] = []
    if arming_report.arming_status != "armed_for_one_shot_m051_metadata_bootstrap":
        blockers.extend(arming_report.blockers or ["m051_one_shot_arming_not_armed"])
    if not command_report.binding_passed:
        blockers.extend(command_report.blockers or ["m051_command_binding_failed"])
    if command_report.command_hash is None:
        blockers.append("command_hash_missing")
    if missing:
        blockers.extend(f"missing_artifact:{item}" for item in missing)
    if mismatches:
        blockers.extend(f"artifact_hash_mismatch:{item}" for item in mismatches)
    return LambdaM051ArtifactBinding(
        binding_passed=not blockers,
        artifact_hashes=artifact_hashes,
        artifact_paths=artifact_paths,
        command_hash=command_report.command_hash,
        arming_hash=_sha256_file(arming),
        command_binding_hash=_sha256_file(command_binding),
        missing_items=sorted(set(missing)),
        hash_mismatches=sorted(set(mismatches)),
        blockers=sorted(set(blockers)),
        warnings=[
            "artifact binding checks local reviewed inputs only",
            "M051A performs no live Lambda operation",
        ],
    )


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_lambda_m051_artifact_binding(path: str | Path) -> LambdaM051ArtifactBinding:
    return LambdaM051ArtifactBinding.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_artifact_binding(
    path: str | Path,
    report: LambdaM051ArtifactBinding,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
