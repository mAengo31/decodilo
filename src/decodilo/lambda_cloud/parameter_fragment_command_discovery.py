"""Local discovery of a future bounded parameter-fragment synthetic command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaParameterFragmentCommandDiscoveryStatus = Literal[
    "found_safe_parameter_fragment_command",
    "no_safe_parameter_fragment_command_found",
]

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
RECOMMENDED_COMMAND = (
    "python -m decodilo.cli dev parameter-fragment-smoke --synthetic "
    "--fragments 2 --max-steps 1 "
    "--out /tmp/decodilo-parameter-fragment-smoke.json"
)


class LambdaParameterFragmentCommandDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M086A"
    discovery_status: LambdaParameterFragmentCommandDiscoveryStatus
    command_category: str | None = None
    argv_tokens: list[str] = Field(default_factory=list)
    local_introspection_commands: list[list[str]] = Field(default_factory=list)
    local_introspection_passed: bool = False
    timeout_seconds: int | None = None
    expected_stdout_bytes_max: int = 8192
    expected_stderr_bytes_max: int = 8192
    generated_workdir_path: str | None = None
    output_artifact_path: str = "/tmp/decodilo-parameter-fragment-smoke.json"
    synthetic_only: bool = True
    fragments: int = 2
    max_steps: int = 1
    deterministic_fragment_definition_required: bool = True
    fragment_update_required: bool = True
    fragment_schedule_required: bool = True
    per_fragment_version_state_required: bool = True
    merge_replay_validation_required: bool = True
    expected_parameter_fragment_semantics: str | None = None
    overlap_claim_allowed: bool = False
    quantization_claim_allowed: bool = False
    no_real_training: bool = True
    no_downloads: bool = True
    no_package_install: bool = True
    no_external_network: bool = True
    no_background_process: bool = True
    gpu_required: bool = False
    safe_reason: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_discovery(self) -> LambdaParameterFragmentCommandDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("parameter-fragment discovery must remain offline")
        if self.discovery_status == "found_safe_parameter_fragment_command":
            if not self.argv_tokens:
                raise ValueError("safe parameter-fragment discovery requires argv tokens")
            if (
                not self.synthetic_only
                or self.fragments != 2
                or self.max_steps != 1
                or not self.deterministic_fragment_definition_required
                or not self.fragment_update_required
                or not self.fragment_schedule_required
                or not self.per_fragment_version_state_required
                or not self.merge_replay_validation_required
                or self.expected_parameter_fragment_semantics
                != "synthetic_vector_fragments"
                or self.overlap_claim_allowed
                or self.quantization_claim_allowed
                or not self.no_real_training
                or not self.no_downloads
                or not self.no_package_install
                or not self.no_external_network
                or not self.no_background_process
                or self.gpu_required
            ):
                raise ValueError("safe parameter-fragment discovery carries unsafe flags")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_parameter_fragment_command(
    *,
    source_root: str | Path,
) -> LambdaParameterFragmentCommandDiscovery:
    root = Path(source_root).resolve()
    commands = [
        [sys.executable, "-m", "decodilo.cli", "--help"],
        [sys.executable, "-m", "decodilo.cli", "dev", "--help"],
    ]
    env = {
        "PYTHONPATH": str(root / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    blockers: list[str] = []
    combined_help = ""
    for command in commands:
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if completed.returncode != 0:
            blockers.append(f"local_introspection_failed:{' '.join(command)}")
        combined_help += completed.stdout + "\n" + completed.stderr + "\n"
    if blockers:
        return LambdaParameterFragmentCommandDiscovery(
            discovery_status="no_safe_parameter_fragment_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=False,
            blockers=blockers,
            warnings=["fix local CLI introspection before authorizing M087R"],
            recommendation=RECOMMENDED_COMMAND,
        )
    candidates = _discover_named_safe_commands(combined_help)
    if not candidates:
        return LambdaParameterFragmentCommandDiscovery(
            discovery_status="no_safe_parameter_fragment_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=True,
            blockers=["no_safe_parameter_fragment_command_found"],
            warnings=[
                "no bounded parameter-fragment command was discovered; "
                "M087R remains not authorized",
            ],
            recommendation=RECOMMENDED_COMMAND,
        )
    return candidates[0].model_copy(
        update={
            "local_introspection_commands": commands,
            "local_introspection_passed": True,
        }
    )


def load_lambda_parameter_fragment_command_discovery(
    path: str | Path,
) -> LambdaParameterFragmentCommandDiscovery:
    return LambdaParameterFragmentCommandDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_parameter_fragment_command_discovery(
    path: str | Path,
    report: LambdaParameterFragmentCommandDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _discover_named_safe_commands(
    help_text: str,
) -> list[LambdaParameterFragmentCommandDiscovery]:
    lower = help_text.lower()
    if "parameter-fragment-smoke" not in lower:
        return []
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "parameter-fragment-smoke",
        "--synthetic",
        "--fragments",
        "2",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-parameter-fragment-smoke.json",
    ]
    return [
        LambdaParameterFragmentCommandDiscovery(
            discovery_status="found_safe_parameter_fragment_command",
            command_category="dev_parameter_fragment_smoke_two_fragments_one_step",
            argv_tokens=argv_tokens,
            timeout_seconds=120,
            generated_workdir_path="/tmp/decodilo-parameter-fragment-smoke",
            expected_parameter_fragment_semantics="synthetic_vector_fragments",
            safe_reason=(
                "explicit parameter-fragment smoke is bounded to two synthetic "
                "fragments, one step, offline, and no GPU"
            ),
        )
    ]
