"""Local discovery of a future bounded DiLoCo optimizer-fidelity command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaDilocoOptimizerCommandDiscoveryStatus = Literal[
    "found_safe_diloco_optimizer_command",
    "no_safe_diloco_optimizer_command_found",
]

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
RECOMMENDED_COMMAND = (
    "python -m decodilo.cli dev diloco-optimizer-smoke --synthetic "
    "--inner-optimizer adamw --outer-optimizer nesterov --max-steps 1 "
    "--out /tmp/decodilo-diloco-optimizer-smoke.json"
)


class LambdaDilocoOptimizerCommandDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M082A"
    discovery_status: LambdaDilocoOptimizerCommandDiscoveryStatus
    command_category: str | None = None
    argv_tokens: list[str] = Field(default_factory=list)
    local_introspection_commands: list[list[str]] = Field(default_factory=list)
    local_introspection_passed: bool = False
    timeout_seconds: int | None = None
    expected_stdout_bytes_max: int = 8192
    expected_stderr_bytes_max: int = 8192
    generated_workdir_path: str | None = None
    output_artifact_path: str = "/tmp/decodilo-diloco-optimizer-smoke.json"
    synthetic_only: bool = True
    inner_optimizer: str | None = None
    outer_optimizer: str | None = None
    max_steps: int = 1
    expected_optimizer_fidelity: str | None = None
    expected_inner_optimizer_semantics: str | None = None
    expected_outer_optimizer_semantics: str | None = None
    pseudo_gradient_semantics_required: bool = True
    persistent_optimizer_state_required: bool = True
    deterministic_reference_check_required: bool = True
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
    def _validate_discovery(self) -> LambdaDilocoOptimizerCommandDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("DiLoCo optimizer discovery must remain offline")
        if self.discovery_status == "found_safe_diloco_optimizer_command":
            if not self.argv_tokens:
                raise ValueError("safe DiLoCo optimizer discovery requires argv tokens")
            if "diloco-smoke" in self.argv_tokens:
                raise ValueError("optimizer discovery must be beyond diloco-smoke")
            if (
                not self.synthetic_only
                or self.inner_optimizer != "adamw"
                or self.outer_optimizer != "nesterov"
                or self.max_steps != 1
                or not self.no_real_training
                or not self.no_downloads
                or not self.no_package_install
                or not self.no_external_network
                or not self.no_background_process
                or self.gpu_required
            ):
                raise ValueError("safe DiLoCo optimizer discovery carries unsafe flags")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_diloco_optimizer_command(
    *,
    source_root: str | Path,
) -> LambdaDilocoOptimizerCommandDiscovery:
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
        return LambdaDilocoOptimizerCommandDiscovery(
            discovery_status="no_safe_diloco_optimizer_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=False,
            blockers=blockers,
            warnings=["fix local CLI introspection before authorizing M083R"],
            recommendation=RECOMMENDED_COMMAND,
        )
    candidates = _discover_named_safe_commands(combined_help)
    if not candidates:
        return LambdaDilocoOptimizerCommandDiscovery(
            discovery_status="no_safe_diloco_optimizer_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=True,
            blockers=["no_safe_diloco_optimizer_command_found"],
            warnings=[
                "no bounded DiLoCo optimizer-fidelity command was discovered; "
                "M083R remains not authorized",
            ],
            recommendation=RECOMMENDED_COMMAND,
        )
    return candidates[0].model_copy(
        update={
            "local_introspection_commands": commands,
            "local_introspection_passed": True,
        }
    )


def load_lambda_diloco_optimizer_command_discovery(
    path: str | Path,
) -> LambdaDilocoOptimizerCommandDiscovery:
    return LambdaDilocoOptimizerCommandDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_diloco_optimizer_command_discovery(
    path: str | Path,
    report: LambdaDilocoOptimizerCommandDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _discover_named_safe_commands(
    help_text: str,
) -> list[LambdaDilocoOptimizerCommandDiscovery]:
    lower = help_text.lower()
    if "diloco-optimizer-smoke" not in lower:
        return []
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "diloco-optimizer-smoke",
        "--synthetic",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-diloco-optimizer-smoke.json",
    ]
    return [
        LambdaDilocoOptimizerCommandDiscovery(
            discovery_status="found_safe_diloco_optimizer_command",
            command_category="dev_diloco_optimizer_smoke_adamw_nesterov_one_step",
            argv_tokens=argv_tokens,
            timeout_seconds=120,
            generated_workdir_path="/tmp/decodilo-diloco-optimizer-smoke",
            inner_optimizer="adamw",
            outer_optimizer="nesterov",
            expected_optimizer_fidelity="optimizer_semantics_smoke",
            expected_inner_optimizer_semantics="adamw",
            expected_outer_optimizer_semantics="nesterov",
            safe_reason=(
                "explicit optimizer smoke is bounded to one synthetic reference "
                "step, offline, no-training, and no GPU"
            ),
        )
    ]
