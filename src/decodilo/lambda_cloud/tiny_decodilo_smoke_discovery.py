"""Local discovery of a future tiny Decodilo smoke command."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaTinyDecodiloSmokeDiscoveryStatus = Literal[
    "found_safe_tiny_smoke_command",
    "safe_tiny_smoke_command_found",
    "no_safe_tiny_smoke_command_found",
]

REMOTE_PYTHONPATH = "/tmp/decodilo-runtime:/tmp/decodilo-src/src"
REMOTE_TINY_SMOKE_REPORT = "/tmp/decodilo-tiny-smoke.json"


class LambdaTinyDecodiloSmokeDiscovery(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M072"
    discovery_status: LambdaTinyDecodiloSmokeDiscoveryStatus
    command_category: str | None = None
    argv_tokens: list[str] = Field(default_factory=list)
    local_introspection_commands: list[list[str]] = Field(default_factory=list)
    local_introspection_passed: bool = False
    timeout_seconds: int | None = None
    expected_stdout_bytes_max: int = 8192
    expected_stderr_bytes_max: int = 8192
    generated_workdir_path: str | None = None
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
    def _validate_discovery(self) -> LambdaTinyDecodiloSmokeDiscovery:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("tiny smoke discovery must remain offline")
        if (
            self.discovery_status
            in {"found_safe_tiny_smoke_command", "safe_tiny_smoke_command_found"}
            and not self.argv_tokens
        ):
            raise ValueError("safe tiny smoke discovery requires argv tokens")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def discover_lambda_tiny_decodilo_smoke_command(
    *,
    source_root: str | Path,
) -> LambdaTinyDecodiloSmokeDiscovery:
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
        return LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="no_safe_tiny_smoke_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=False,
            blockers=blockers,
            warnings=["fix local CLI introspection before authorizing M073R"],
        )
    candidates = _discover_named_safe_commands(combined_help)
    if not candidates:
        return LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="no_safe_tiny_smoke_command_found",
            local_introspection_commands=commands,
            local_introspection_passed=True,
            blockers=["no_safe_tiny_smoke_command_found"],
            warnings=[
                "no real tiny Decodilo smoke command was discovered; add an explicit "
                "bounded no-network CLI smoke before M073R"
            ],
        )
    local_report = Path("/tmp/decodilo-tiny-smoke-discovery-local.json")
    local_command = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "dev",
        "tiny-smoke",
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
        return LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="no_safe_tiny_smoke_command_found",
            local_introspection_commands=[*commands, local_command],
            local_introspection_passed=False,
            blockers=["local_tiny_smoke_validation_failed"],
            warnings=["tiny smoke command was present but failed local validation"],
        )
    return candidates[0].model_copy(
        update={
            "local_introspection_commands": [*commands, local_command],
            "local_introspection_passed": True,
        }
    )


def load_lambda_tiny_decodilo_smoke_discovery(
    path: str | Path,
) -> LambdaTinyDecodiloSmokeDiscovery:
    return LambdaTinyDecodiloSmokeDiscovery.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_tiny_decodilo_smoke_discovery(
    path: str | Path,
    report: LambdaTinyDecodiloSmokeDiscovery,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _discover_named_safe_commands(help_text: str) -> list[LambdaTinyDecodiloSmokeDiscovery]:
    lower = help_text.lower()
    if "tiny-smoke" not in lower:
        return []
    argv_tokens = [
        "env",
        f"PYTHONPATH={REMOTE_PYTHONPATH}",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "tiny-smoke",
        "--synthetic",
        "--max-steps",
        "1",
        "--out",
        REMOTE_TINY_SMOKE_REPORT,
    ]
    return [
        LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="found_safe_tiny_smoke_command",
            command_category="dev_tiny_smoke_synthetic",
            argv_tokens=argv_tokens,
            timeout_seconds=30,
            generated_workdir_path="/tmp/decodilo-tiny-smoke",
            safe_reason=(
                "dev tiny-smoke is a bounded synthetic in-memory command with no "
                "network, package install, download, GPU, torch, or training path"
            ),
            warnings=[
                "future M073R still requires fresh live discovery and explicit operator approval",
            ],
        )
    ]
