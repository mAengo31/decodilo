"""Local discovery of a future bounded integrated synthetic DiLoCo command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaIntegratedDilocoCommandDiscoveryStatus = Literal[
    "found_safe_integrated_diloco_command",
    "no_safe_integrated_diloco_command_found",
]

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
RECOMMENDED_COMMAND = (
    "python -m decodilo.cli dev integrated-diloco-smoke --synthetic "
    "--learners 1 --sync-rounds 1 --inner-optimizer adamw "
    "--outer-optimizer nesterov --max-steps 1 "
    "--out /tmp/decodilo-integrated-diloco-smoke.json"
)


class LambdaIntegratedDilocoCommandDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M084A"
    discovery_status: LambdaIntegratedDilocoCommandDiscoveryStatus
    command_category: str | None = None
    argv_tokens: list[str] = Field(default_factory=list)
    local_introspection_commands: list[list[str]] = Field(default_factory=list)
    local_introspection_passed: bool = False
    timeout_seconds: int | None = None
    expected_stdout_bytes_max: int = 8192
    expected_stderr_bytes_max: int = 8192
    generated_workdir_path: str | None = None
    output_artifact_path: str = "/tmp/decodilo-integrated-diloco-smoke.json"
    synthetic_only: bool = True
    learners: int = 1
    sync_rounds: int = 1
    inner_optimizer: str | None = None
    outer_optimizer: str | None = None
    expected_integrated_fidelity: str | None = None
    max_steps: int = 1
    learner_syncer_protocol_required: bool = True
    diloco_shaped_sync_round_required: bool = True
    pseudo_gradient_semantics_required: bool = True
    optimizer_state_roundtrip_required: bool = True
    replay_or_metric_validation_required: bool = True
    parameter_fragment_claim_allowed: bool = False
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
    def _validate_discovery(self) -> LambdaIntegratedDilocoCommandDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("integrated DiLoCo discovery must remain offline")
        if self.discovery_status == "found_safe_integrated_diloco_command":
            if not self.argv_tokens:
                raise ValueError("safe integrated DiLoCo discovery requires argv tokens")
            if (
                not self.synthetic_only
                or self.learners != 1
                or self.sync_rounds != 1
                or self.inner_optimizer != "adamw"
                or self.outer_optimizer != "nesterov"
                or self.expected_integrated_fidelity
                != "integrated_optimizer_protocol_smoke"
                or self.max_steps != 1
                or not self.no_real_training
                or not self.no_downloads
                or not self.no_package_install
                or not self.no_external_network
                or not self.no_background_process
                or self.gpu_required
            ):
                raise ValueError("safe integrated DiLoCo discovery carries unsafe flags")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_integrated_diloco_command(
    *,
    source_root: str | Path,
) -> LambdaIntegratedDilocoCommandDiscovery:
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
        return LambdaIntegratedDilocoCommandDiscovery(
            discovery_status="no_safe_integrated_diloco_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=False,
            blockers=blockers,
            warnings=["fix local CLI introspection before authorizing M085R"],
            recommendation=RECOMMENDED_COMMAND,
        )
    candidates = _discover_named_safe_commands(combined_help)
    if not candidates:
        return LambdaIntegratedDilocoCommandDiscovery(
            discovery_status="no_safe_integrated_diloco_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=True,
            blockers=["no_safe_integrated_diloco_command_found"],
            warnings=[
                "no bounded integrated DiLoCo command was discovered; "
                "M085R remains not authorized",
            ],
            recommendation=RECOMMENDED_COMMAND,
        )
    return candidates[0].model_copy(
        update={
            "local_introspection_commands": commands,
            "local_introspection_passed": True,
        }
    )


def load_lambda_integrated_diloco_command_discovery(
    path: str | Path,
) -> LambdaIntegratedDilocoCommandDiscovery:
    return LambdaIntegratedDilocoCommandDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_integrated_diloco_command_discovery(
    path: str | Path,
    report: LambdaIntegratedDilocoCommandDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _discover_named_safe_commands(
    help_text: str,
) -> list[LambdaIntegratedDilocoCommandDiscovery]:
    lower = help_text.lower()
    if "integrated-diloco-smoke" not in lower:
        return []
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "integrated-diloco-smoke",
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-integrated-diloco-smoke.json",
    ]
    return [
        LambdaIntegratedDilocoCommandDiscovery(
            discovery_status="found_safe_integrated_diloco_command",
            command_category="dev_integrated_diloco_smoke_one_step",
            argv_tokens=argv_tokens,
            timeout_seconds=120,
            generated_workdir_path="/tmp/decodilo-integrated-diloco-smoke",
            inner_optimizer="adamw",
            outer_optimizer="nesterov",
            expected_integrated_fidelity="integrated_optimizer_protocol_smoke",
            safe_reason=(
                "explicit integrated smoke is bounded to one synthetic learner, "
                "one sync round, AdamW/Nesterov semantics, offline, and no GPU"
            ),
        )
    ]
