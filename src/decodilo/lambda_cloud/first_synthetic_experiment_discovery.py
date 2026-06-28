"""Local discovery of a future bounded synthetic runtime experiment command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaFirstSyntheticExperimentDiscoveryStatus = Literal[
    "found_safe_first_synthetic_experiment_command",
    "no_safe_first_synthetic_experiment_command_found",
]

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
REMOTE_SYNTHETIC_EXPERIMENT_REPORT = "/tmp/decodilo-synthetic-experiment.json"


class LambdaFirstSyntheticExperimentDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M076"
    discovery_status: LambdaFirstSyntheticExperimentDiscoveryStatus
    command_category: str | None = None
    argv_tokens: list[str] = Field(default_factory=list)
    local_introspection_commands: list[list[str]] = Field(default_factory=list)
    local_introspection_passed: bool = False
    timeout_seconds: int | None = None
    expected_stdout_bytes_max: int = 8192
    expected_stderr_bytes_max: int = 8192
    generated_workdir_path: str | None = None
    safe_reason: str | None = None
    synthetic_only: bool = True
    no_real_training: bool = True
    no_downloads: bool = True
    no_package_install: bool = True
    no_external_network: bool = True
    no_background_process: bool = True
    gpu_required: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_discovery(self) -> LambdaFirstSyntheticExperimentDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("first synthetic experiment discovery must remain offline")
        if self.discovery_status == "found_safe_first_synthetic_experiment_command":
            if not self.argv_tokens:
                raise ValueError("safe first synthetic discovery requires argv tokens")
            if (
                not self.synthetic_only
                or not self.no_real_training
                or not self.no_downloads
                or not self.no_package_install
                or not self.no_external_network
                or not self.no_background_process
                or self.gpu_required
            ):
                raise ValueError("safe first synthetic discovery carries unsafe flags")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_first_synthetic_experiment_command(
    *,
    source_root: str | Path,
) -> LambdaFirstSyntheticExperimentDiscovery:
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
        return LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="no_safe_first_synthetic_experiment_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=False,
            blockers=blockers,
            warnings=[
                "fix local CLI introspection before authorizing M077R",
            ],
            recommendation=(
                "Add an explicit bounded offline synthetic experiment command before "
                "M077R."
            ),
        )
    candidates = _discover_named_safe_commands(combined_help)
    if not candidates:
        return LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="no_safe_first_synthetic_experiment_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=True,
            blockers=["no_safe_first_synthetic_experiment_command_found"],
            warnings=[
                "no bounded synthetic Decodilo experiment command was discovered; "
                "M077R remains not authorized",
            ],
            recommendation=(
                "Add a command such as `python -m decodilo.cli dev "
                "synthetic-experiment --synthetic --max-steps 1 --out "
                "/tmp/decodilo-synthetic-experiment.json`, then rerun offline "
                "discovery."
            ),
        )
    local_report = Path("/tmp/decodilo-synthetic-experiment-discovery-local.json")
    local_command = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "dev",
        "synthetic-experiment",
        "--synthetic",
        "--max-steps",
        "1",
        "--out",
        str(local_report),
    ]
    completed = subprocess.run(
        local_command,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    if completed.returncode != 0 or not local_report.exists():
        return LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="no_safe_first_synthetic_experiment_command_found",
            local_introspection_commands=[*commands, local_command],
            local_introspection_passed=False,
            blockers=["local_synthetic_experiment_validation_failed"],
            warnings=[
                "synthetic-experiment command was present but failed local validation; "
                "M077R remains not authorized",
            ],
        )
    validation = json.loads(local_report.read_text(encoding="utf-8"))
    unsafe = [
        name
        for name in (
            "network_used",
            "package_install_attempted",
            "download_attempted",
            "training_attempted",
            "real_model_training_attempted",
            "torch_required",
            "gpu_required",
            "background_process_started",
            "launch_ready",
            "launch_allowed",
        )
        if bool(validation.get(name))
    ]
    if (
        validation.get("synthetic_experiment_status") != "passed"
        or validation.get("synthetic") is not True
        or validation.get("learner_or_runtime_check_passed") is not True
        or validation.get("update_or_commit_check_passed") is not True
        or validation.get("replay_or_metric_check_passed") is not True
        or unsafe
    ):
        return LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="no_safe_first_synthetic_experiment_command_found",
            local_introspection_commands=[*commands, local_command],
            local_introspection_passed=False,
            blockers=["local_synthetic_experiment_safety_validation_failed", *unsafe],
            warnings=["synthetic-experiment command failed local safety validation"],
        )
    return candidates[0].model_copy(
        update={
            "local_introspection_commands": [*commands, local_command],
            "local_introspection_passed": True,
        }
    )


def load_lambda_first_synthetic_experiment_discovery(
    path: str | Path,
) -> LambdaFirstSyntheticExperimentDiscovery:
    return LambdaFirstSyntheticExperimentDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_first_synthetic_experiment_discovery(
    path: str | Path,
    report: LambdaFirstSyntheticExperimentDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _discover_named_safe_commands(
    help_text: str,
) -> list[LambdaFirstSyntheticExperimentDiscovery]:
    lower = help_text.lower()
    if "synthetic-experiment" not in lower:
        return []
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "synthetic-experiment",
        "--synthetic",
        "--max-steps",
        "1",
        "--out",
        REMOTE_SYNTHETIC_EXPERIMENT_REPORT,
    ]
    return [
        LambdaFirstSyntheticExperimentDiscovery(
            discovery_status="found_safe_first_synthetic_experiment_command",
            command_category="dev_synthetic_experiment_one_step",
            argv_tokens=argv_tokens,
            timeout_seconds=120,
            generated_workdir_path="/tmp/decodilo-synthetic-experiment",
            safe_reason=(
                "explicit dev synthetic-experiment command is bounded to one step, "
                "synthetic-only, local/offline, and writes one JSON artifact"
            ),
        )
    ]
