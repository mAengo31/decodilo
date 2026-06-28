"""Local discovery of a complete bounded synthetic DiLoCo experiment command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-bounded-diloco-experiment.json"
RECOMMENDED_COMMAND = (
    "python -m decodilo.cli dev bounded-diloco-experiment --synthetic "
    "--learners 1 --sync-rounds 1 --fragments 2 --inner-optimizer adamw "
    "--outer-optimizer nesterov --max-steps 1 "
    "--out /tmp/decodilo-bounded-diloco-experiment.json"
)

LambdaBoundedDilocoExperimentDiscoveryStatus = Literal[
    "found_safe_bounded_diloco_experiment_command",
    "no_safe_bounded_diloco_experiment_command_found",
]


class LambdaBoundedDilocoExperimentCommandDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M088"
    discovery_status: LambdaBoundedDilocoExperimentDiscoveryStatus
    command_category: str | None = None
    argv_tokens: list[str] = Field(default_factory=list)
    local_introspection_commands: list[list[str]] = Field(default_factory=list)
    local_introspection_passed: bool = False
    timeout_seconds: int | None = None
    expected_stdout_bytes_max: int = 8192
    expected_stderr_bytes_max: int = 8192
    output_artifact_path: str = OUTPUT_ARTIFACT_PATH
    synthetic_only: bool = True
    learners: int = 1
    sync_rounds: int = 1
    fragments: int = 2
    inner_optimizer: str = "adamw"
    outer_optimizer: str = "nesterov"
    max_steps: int = 1
    learner_syncer_protocol_required: bool = True
    adamw_required: bool = True
    nesterov_required: bool = True
    pseudo_gradient_required: bool = True
    parameter_fragments_required: bool = True
    replay_metric_validation_required: bool = True
    no_real_training: bool = True
    no_downloads: bool = True
    no_package_install: bool = True
    no_external_network: bool = True
    no_background_process: bool = True
    no_new_independent_smoke_category: bool = True
    gpu_required: bool = False
    safe_reason: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_discovery(self) -> LambdaBoundedDilocoExperimentCommandDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("bounded experiment discovery must remain offline")
        if self.discovery_status == "found_safe_bounded_diloco_experiment_command":
            if not self.argv_tokens:
                raise ValueError("safe bounded experiment discovery requires argv tokens")
            if (
                not self.synthetic_only
                or self.learners != 1
                or self.sync_rounds != 1
                or self.fragments != 2
                or self.inner_optimizer != "adamw"
                or self.outer_optimizer != "nesterov"
                or self.max_steps != 1
                or not self.learner_syncer_protocol_required
                or not self.adamw_required
                or not self.nesterov_required
                or not self.pseudo_gradient_required
                or not self.parameter_fragments_required
                or not self.replay_metric_validation_required
                or not self.no_real_training
                or not self.no_downloads
                or not self.no_package_install
                or not self.no_external_network
                or not self.no_background_process
                or not self.no_new_independent_smoke_category
                or self.gpu_required
            ):
                raise ValueError("safe bounded experiment discovery carries unsafe flags")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_bounded_diloco_experiment_command(
    *,
    source_root: str | Path,
) -> LambdaBoundedDilocoExperimentCommandDiscovery:
    root = Path(source_root).resolve()
    commands = [
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
        return LambdaBoundedDilocoExperimentCommandDiscovery(
            discovery_status="no_safe_bounded_diloco_experiment_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=False,
            blockers=blockers,
            warnings=["fix local CLI introspection before authorizing M089R"],
            recommendation=RECOMMENDED_COMMAND,
        )
    candidates = _discover_named_safe_commands(combined_help)
    if not candidates:
        return LambdaBoundedDilocoExperimentCommandDiscovery(
            discovery_status="no_safe_bounded_diloco_experiment_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=True,
            blockers=["no_safe_bounded_diloco_experiment_command_found"],
            warnings=[
                "no complete bounded synthetic DiLoCo experiment command was "
                "discovered; M089R remains not authorized",
                "do not add another independent scaffold category by default",
            ],
            recommendation=RECOMMENDED_COMMAND,
        )
    return candidates[0].model_copy(
        update={
            "local_introspection_commands": commands,
            "local_introspection_passed": True,
        }
    )


def load_lambda_bounded_diloco_experiment_command_discovery(
    path: str | Path,
) -> LambdaBoundedDilocoExperimentCommandDiscovery:
    return LambdaBoundedDilocoExperimentCommandDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_bounded_diloco_experiment_command_discovery(
    path: str | Path,
    report: LambdaBoundedDilocoExperimentCommandDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _discover_named_safe_commands(
    help_text: str,
) -> list[LambdaBoundedDilocoExperimentCommandDiscovery]:
    lower = help_text.lower()
    if "bounded-diloco-experiment" not in lower:
        return []
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "bounded-diloco-experiment",
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--fragments",
        "2",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
        "--out",
        OUTPUT_ARTIFACT_PATH,
    ]
    return [
        LambdaBoundedDilocoExperimentCommandDiscovery(
            discovery_status="found_safe_bounded_diloco_experiment_command",
            command_category="dev_bounded_diloco_experiment_one_step",
            argv_tokens=argv_tokens,
            timeout_seconds=180,
            safe_reason=(
                "complete bounded experiment command combines protocol, optimizer, "
                "and synthetic fragment semantics in one offline one-step artifact"
            ),
        )
    ]
