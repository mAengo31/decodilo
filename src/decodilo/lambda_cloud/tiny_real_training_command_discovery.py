"""Local discovery of a bounded tiny real-training smoke command."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.dev.tiny_real_training_smoke import (
    load_tiny_real_training_smoke_report,
)

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-tiny-real-training-smoke.json"
RECOMMENDED_COMMAND = (
    "python -m decodilo.cli dev tiny-real-training-smoke --synthetic "
    "--model tiny-linear --steps 1 --optimizer adamw "
    "--out /tmp/decodilo-tiny-real-training-smoke.json"
)

LambdaTinyRealTrainingDiscoveryStatus = Literal[
    "found_safe_tiny_real_training_command",
    "no_safe_tiny_real_training_command_found",
]


class LambdaTinyRealTrainingCommandDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M092"
    discovery_status: LambdaTinyRealTrainingDiscoveryStatus
    command_category: str | None = None
    argv_tokens: list[str] = Field(default_factory=list)
    local_introspection_commands: list[list[str]] = Field(default_factory=list)
    local_smoke_command: list[str] = Field(default_factory=list)
    local_introspection_passed: bool = False
    local_smoke_passed: bool = False
    timeout_seconds: int | None = None
    expected_stdout_bytes_max: int = 8192
    expected_stderr_bytes_max: int = 8192
    output_artifact_path: str = OUTPUT_ARTIFACT_PATH
    synthetic_only: bool = True
    model: str = "tiny-linear"
    steps: int = 1
    optimizer: str = "adamw"
    cpu_only: bool = True
    torch_required: bool = False
    gpu_required: bool = False
    real_training_mechanics_exercised: bool = False
    training_attempted: bool = False
    no_external_network: bool = True
    no_package_install: bool = True
    no_downloads: bool = True
    no_dataset_download: bool = True
    no_model_download: bool = True
    no_background_process: bool = True
    bounded_runtime: bool = False
    bounded_output: bool = False
    safe_reason: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendation: str | None = None
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_discovery(self) -> LambdaTinyRealTrainingCommandDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("tiny real training discovery must remain offline")
        if self.discovery_status == "found_safe_tiny_real_training_command":
            if not self.argv_tokens:
                raise ValueError("safe tiny real training discovery requires argv")
            if (
                not self.local_smoke_passed
                or not self.synthetic_only
                or self.model != "tiny-linear"
                or self.steps != 1
                or self.optimizer != "adamw"
                or not self.cpu_only
                or self.torch_required
                or self.gpu_required
                or not self.training_attempted
                or not self.real_training_mechanics_exercised
                or not self.no_external_network
                or not self.no_package_install
                or not self.no_downloads
                or not self.no_dataset_download
                or not self.no_model_download
                or not self.no_background_process
                or not self.bounded_runtime
                or not self.bounded_output
            ):
                raise ValueError("safe tiny real training discovery carries bad flags")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_tiny_real_training_command(
    *,
    source_root: str | Path,
) -> LambdaTinyRealTrainingCommandDiscovery:
    root = Path(source_root).resolve()
    env = {
        "PYTHONPATH": str(root / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    help_command = [sys.executable, "-m", "decodilo.cli", "dev", "--help"]
    blockers: list[str] = []
    completed = subprocess.run(
        help_command,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    help_text = completed.stdout + "\n" + completed.stderr
    if completed.returncode != 0:
        blockers.append("local_cli_help_failed")
    if "tiny-real-training-smoke" not in help_text:
        blockers.append("tiny_real_training_smoke_not_discoverable")
    if blockers:
        return LambdaTinyRealTrainingCommandDiscovery(
            discovery_status="no_safe_tiny_real_training_command_found",
            local_introspection_commands=[help_command],
            local_introspection_passed=False,
            blockers=blockers,
            recommendation=RECOMMENDED_COMMAND,
        )

    with tempfile.TemporaryDirectory(prefix="decodilo-tiny-real-training-discovery-") as tmp:
        out_path = Path(tmp) / "tiny-real-training-smoke.json"
        smoke_command = [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "tiny-real-training-smoke",
            "--synthetic",
            "--model",
            "tiny-linear",
            "--steps",
            "1",
            "--optimizer",
            "adamw",
            "--out",
            str(out_path),
        ]
        smoke = subprocess.run(
            smoke_command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if smoke.returncode != 0:
            blockers.append("local_tiny_real_training_smoke_failed")
        if not out_path.exists():
            blockers.append("local_tiny_real_training_artifact_missing")
        if blockers:
            return LambdaTinyRealTrainingCommandDiscovery(
                discovery_status="no_safe_tiny_real_training_command_found",
                local_introspection_commands=[help_command],
                local_smoke_command=smoke_command,
                local_introspection_passed=True,
                local_smoke_passed=False,
                blockers=blockers,
                recommendation=RECOMMENDED_COMMAND,
            )
        report = load_tiny_real_training_smoke_report(out_path)

    local_smoke_passed = report.tiny_real_training_smoke_status == "passed"
    if not local_smoke_passed:
        blockers.append("local_tiny_real_training_smoke_not_passed")
    if report.torch_required:
        blockers.append("tiny_real_training_smoke_requires_torch")
    if blockers:
        return LambdaTinyRealTrainingCommandDiscovery(
            discovery_status="no_safe_tiny_real_training_command_found",
            local_introspection_commands=[help_command],
            local_smoke_command=smoke_command,
            local_introspection_passed=True,
            local_smoke_passed=local_smoke_passed,
            torch_required=report.torch_required,
            gpu_required=report.gpu_required,
            blockers=blockers,
            recommendation=RECOMMENDED_COMMAND,
        )
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "tiny-real-training-smoke",
        "--synthetic",
        "--model",
        "tiny-linear",
        "--steps",
        "1",
        "--optimizer",
        "adamw",
        "--out",
        OUTPUT_ARTIFACT_PATH,
    ]
    return LambdaTinyRealTrainingCommandDiscovery(
        discovery_status="found_safe_tiny_real_training_command",
        command_category="dev_tiny_real_training_smoke_one_step",
        argv_tokens=argv_tokens,
        local_introspection_commands=[help_command],
        local_smoke_command=smoke_command,
        local_introspection_passed=True,
        local_smoke_passed=True,
        timeout_seconds=60,
        torch_required=report.torch_required,
        gpu_required=report.gpu_required,
        real_training_mechanics_exercised=report.real_training_mechanics_exercised,
        training_attempted=report.training_attempted,
        bounded_runtime=True,
        bounded_output=report.artifact_bytes <= 32768,
        safe_reason=(
            "one-step pure-Python tiny-linear AdamW smoke exercises forward, "
            "loss, gradient, optimizer update, optimizer state, and replay checks"
        ),
    )


def load_lambda_tiny_real_training_command_discovery(
    path: str | Path,
) -> LambdaTinyRealTrainingCommandDiscovery:
    return LambdaTinyRealTrainingCommandDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_tiny_real_training_command_discovery(
    path: str | Path,
    report: LambdaTinyRealTrainingCommandDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
