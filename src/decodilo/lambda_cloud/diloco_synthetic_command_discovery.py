"""Local discovery of a future bounded DiLoCo-shaped synthetic command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaDilocoSyntheticCommandDiscoveryStatus = Literal[
    "found_safe_diloco_synthetic_command",
    "no_safe_diloco_synthetic_command_found",
]

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
RECOMMENDED_COMMAND = (
    "python -m decodilo.cli dev diloco-smoke --synthetic --learners 1 "
    "--sync-rounds 1 --max-steps 1 --out /tmp/decodilo-diloco-smoke.json"
)


class LambdaDilocoSyntheticCommandDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M080"
    discovery_status: LambdaDilocoSyntheticCommandDiscoveryStatus
    command_category: str | None = None
    argv_tokens: list[str] = Field(default_factory=list)
    local_introspection_commands: list[list[str]] = Field(default_factory=list)
    local_introspection_passed: bool = False
    timeout_seconds: int | None = None
    expected_stdout_bytes_max: int = 8192
    expected_stderr_bytes_max: int = 8192
    generated_workdir_path: str | None = None
    learners: int = 1
    sync_rounds: int = 1
    max_steps: int = 1
    output_artifact_path: str = "/tmp/decodilo-diloco-smoke.json"
    safe_reason: str | None = None
    synthetic_only: bool = True
    one_learner_default: bool = True
    one_syncer_role_default: bool = True
    one_sync_update_round_default: bool = True
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
    def _validate_discovery(self) -> LambdaDilocoSyntheticCommandDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("DiLoCo synthetic discovery must remain offline")
        if self.discovery_status == "found_safe_diloco_synthetic_command":
            if not self.argv_tokens:
                raise ValueError("safe DiLoCo discovery requires argv tokens")
            if "learner-syncer-smoke" in self.argv_tokens:
                raise ValueError("DiLoCo discovery must be beyond learner-syncer-smoke")
            if (
                not self.synthetic_only
                or not self.one_learner_default
                or not self.one_syncer_role_default
                or not self.one_sync_update_round_default
                or not self.no_real_training
                or not self.no_downloads
                or not self.no_package_install
                or not self.no_external_network
                or not self.no_background_process
                or self.gpu_required
            ):
                raise ValueError("safe DiLoCo discovery carries unsafe flags")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_diloco_synthetic_command(
    *,
    source_root: str | Path,
) -> LambdaDilocoSyntheticCommandDiscovery:
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
        return LambdaDilocoSyntheticCommandDiscovery(
            discovery_status="no_safe_diloco_synthetic_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=False,
            blockers=blockers,
            warnings=["fix local CLI introspection before authorizing M081R"],
            recommendation=RECOMMENDED_COMMAND,
        )
    candidates = _discover_named_safe_commands(combined_help)
    if not candidates:
        return LambdaDilocoSyntheticCommandDiscovery(
            discovery_status="no_safe_diloco_synthetic_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=True,
            blockers=["no_safe_diloco_synthetic_command_found"],
            warnings=[
                "no bounded DiLoCo-shaped synthetic command was discovered; "
                "M081R remains not authorized",
            ],
            recommendation=RECOMMENDED_COMMAND,
        )
    return candidates[0].model_copy(
        update={
            "local_introspection_commands": commands,
            "local_introspection_passed": True,
        }
    )


def load_lambda_diloco_synthetic_command_discovery(
    path: str | Path,
) -> LambdaDilocoSyntheticCommandDiscovery:
    return LambdaDilocoSyntheticCommandDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_synthetic_command_discovery(
    path: str | Path,
    report: LambdaDilocoSyntheticCommandDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _discover_named_safe_commands(
    help_text: str,
) -> list[LambdaDilocoSyntheticCommandDiscovery]:
    lower = help_text.lower()
    if "diloco-smoke" not in lower:
        return []
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "diloco-smoke",
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-diloco-smoke.json",
    ]
    return [
        LambdaDilocoSyntheticCommandDiscovery(
            discovery_status="found_safe_diloco_synthetic_command",
            command_category="dev_diloco_smoke_one_learner_one_round",
            argv_tokens=argv_tokens,
            timeout_seconds=120,
            generated_workdir_path="/tmp/decodilo-diloco-smoke",
            learners=1,
            sync_rounds=1,
            max_steps=1,
            output_artifact_path="/tmp/decodilo-diloco-smoke.json",
            safe_reason=(
                "explicit diloco-smoke command is bounded to one learner, one "
                "sync/update round, synthetic-only, offline, and no-training"
            ),
        )
    ]
