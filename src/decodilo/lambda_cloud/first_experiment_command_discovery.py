"""Local discovery of the first safe remote Decodilo experiment command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
REMOTE_CI_PROFILE_REPORT = "/tmp/decodilo-first-experiment-ci-profile-report.json"

LambdaFirstExperimentCommandDiscoveryStatus = Literal[
    "safe_experiment_command_found",
    "no_safe_experiment_command_found",
]


class LambdaFirstExperimentCommandDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M070"
    discovery_status: LambdaFirstExperimentCommandDiscoveryStatus
    command_category: str | None = None
    argv_tokens: list[str] = Field(default_factory=list)
    local_validation_command: list[str] = Field(default_factory=list)
    local_validation_passed: bool = False
    timeout_seconds: int | None = None
    expected_stdout_bytes_max: int = 8192
    expected_stderr_bytes_max: int = 8192
    safe_reason: str | None = None
    no_training: bool = True
    no_downloads: bool = True
    no_package_install: bool = True
    no_external_network: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_discovery(self) -> LambdaFirstExperimentCommandDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("first experiment command discovery must remain offline")
        if self.discovery_status == "safe_experiment_command_found" and not self.argv_tokens:
            raise ValueError("safe command discovery requires argv tokens")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_first_experiment_command(
    *,
    source_root: str | Path,
) -> LambdaFirstExperimentCommandDiscovery:
    root = Path(source_root).resolve()
    cli_path = root / "src" / "decodilo" / "cli.py"
    blockers: list[str] = []
    if not cli_path.exists():
        blockers.append("decodilo_cli_not_found")
    local_out = Path("/tmp/decodilo-first-experiment-command-discovery-local.json")
    local_command = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "dev",
        "ci-profile-report",
        "--out",
        str(local_out),
    ]
    validation_passed = False
    if not blockers:
        env = {
            "PYTHONPATH": str(root / "src"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        completed = subprocess.run(
            local_command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        validation_passed = completed.returncode == 0 and local_out.exists()
        if not validation_passed:
            blockers.append("local_ci_profile_report_validation_failed")
    if blockers:
        return LambdaFirstExperimentCommandDiscovery(
            discovery_status="no_safe_experiment_command_found",
            local_validation_command=local_command,
            local_validation_passed=False,
            blockers=blockers,
            warnings=["add a tiny remote-safe Decodilo smoke command before M071R"],
        )
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "ci-profile-report",
        "--out",
        REMOTE_CI_PROFILE_REPORT,
    ]
    return LambdaFirstExperimentCommandDiscovery(
        discovery_status="safe_experiment_command_found",
        command_category="cli_profile_report_command",
        argv_tokens=argv_tokens,
        local_validation_command=local_command,
        local_validation_passed=validation_passed,
        timeout_seconds=30,
        safe_reason=(
            "validated local CLI profile report command exercises Decodilo beyond help "
            "without training, downloads, package install, or background execution"
        ),
        warnings=[
            "future M071R still requires fresh live discovery and explicit operator approval",
        ],
    )


def load_lambda_first_experiment_command_discovery(
    path: str | Path,
) -> LambdaFirstExperimentCommandDiscovery:
    return LambdaFirstExperimentCommandDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_first_experiment_command_discovery(
    path: str | Path,
    report: LambdaFirstExperimentCommandDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
