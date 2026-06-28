"""Local discovery of a future next bounded synthetic experiment command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaNextSyntheticExperimentDiscoveryStatus = Literal[
    "found_safe_next_synthetic_experiment_command",
    "no_safe_next_synthetic_experiment_command_found",
]

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
RECOMMENDED_COMMAND = (
    "python -m decodilo.cli dev learner-syncer-smoke --synthetic --max-steps 1 "
    "--out /tmp/decodilo-learner-syncer-smoke.json"
)


class LambdaNextSyntheticExperimentDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M078"
    discovery_status: LambdaNextSyntheticExperimentDiscoveryStatus
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
    def _validate_discovery(self) -> LambdaNextSyntheticExperimentDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("next synthetic experiment discovery must remain offline")
        if self.discovery_status == "found_safe_next_synthetic_experiment_command":
            if not self.argv_tokens:
                raise ValueError("safe next synthetic discovery requires argv tokens")
            if (
                not self.synthetic_only
                or not self.no_real_training
                or not self.no_downloads
                or not self.no_package_install
                or not self.no_external_network
                or not self.no_background_process
                or self.gpu_required
            ):
                raise ValueError("safe next synthetic discovery carries unsafe flags")
            if "synthetic-experiment" in self.argv_tokens:
                raise ValueError("next synthetic discovery must be beyond synthetic-experiment")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_next_synthetic_experiment_command(
    *,
    source_root: str | Path,
) -> LambdaNextSyntheticExperimentDiscovery:
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
        return LambdaNextSyntheticExperimentDiscovery(
            discovery_status="no_safe_next_synthetic_experiment_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=False,
            blockers=blockers,
            warnings=["fix local CLI introspection before authorizing M079R"],
            recommendation=RECOMMENDED_COMMAND,
        )
    candidates = _discover_named_safe_commands(combined_help)
    if not candidates:
        return LambdaNextSyntheticExperimentDiscovery(
            discovery_status="no_safe_next_synthetic_experiment_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=True,
            blockers=["no_safe_next_synthetic_experiment_command_found"],
            warnings=[
                "no bounded learner/syncer or DiLoCo-shaped synthetic command was "
                "discovered; M079R remains not authorized",
            ],
            recommendation=RECOMMENDED_COMMAND,
        )
    return candidates[0].model_copy(
        update={
            "local_introspection_commands": commands,
            "local_introspection_passed": True,
        }
    )


def load_lambda_next_synthetic_experiment_discovery(
    path: str | Path,
) -> LambdaNextSyntheticExperimentDiscovery:
    return LambdaNextSyntheticExperimentDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_next_synthetic_experiment_discovery(
    path: str | Path,
    report: LambdaNextSyntheticExperimentDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _discover_named_safe_commands(
    help_text: str,
) -> list[LambdaNextSyntheticExperimentDiscovery]:
    lower = help_text.lower()
    if "learner-syncer-smoke" not in lower:
        return []
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "learner-syncer-smoke",
        "--synthetic",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-learner-syncer-smoke.json",
    ]
    return [
        LambdaNextSyntheticExperimentDiscovery(
            discovery_status="found_safe_next_synthetic_experiment_command",
            command_category="dev_learner_syncer_smoke_one_step",
            argv_tokens=argv_tokens,
            timeout_seconds=120,
            generated_workdir_path="/tmp/decodilo-learner-syncer-smoke",
            safe_reason=(
                "explicit learner-syncer-smoke command is bounded to one synthetic "
                "step, local/offline, no-training, and writes one JSON artifact"
            ),
        )
    ]
