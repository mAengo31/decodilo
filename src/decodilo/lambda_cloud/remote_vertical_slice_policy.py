"""M066R fail-fast remote Decodilo vertical-slice policy."""

from __future__ import annotations

import hashlib
import importlib
import json
import re
import shlex
import subprocess
import tarfile
import tempfile
import time
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.real_launch_result import redact_instance_id
from decodilo.lambda_cloud.ssh_connectivity_m056_plan import (
    M056_SELECTED_CANDIDATE,
    M056_SELECTED_REGION,
)
from decodilo.lambda_cloud.ssh_connectivity_probe import (
    _default_tcp_connect_checker,
    _isolated_known_hosts_path,
    _redacted_stderr_fields,
    _wait_for_ssh_port_ready,
)
from decodilo.lambda_cloud.ssh_failure_classifier import classify_ssh_failure
from decodilo.lambda_cloud.ssh_host_discovery import LambdaSSHHostDiscoveryResult
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    load_lambda_existing_ssh_key_selection,
)
from decodilo.pricing.snapshots import PriceSnapshot, SnapshotPriceRecord, load_price_snapshot

M066R_MILESTONE = "M066R"
M066R_ARMED_FOR = "m066r_remote_decodilo_vertical_slice_single_launch_attempt"
M066R_MANIFEST_COMMAND_LABEL = "m066r-command-manifest"
M067R_MILESTONE = "M067R"
M067R_ARMED_FOR = "m067r_source_bundle_vertical_slice_single_launch_attempt"
M067R_MANIFEST_COMMAND_LABEL = "m067r-source-bundle-command-manifest"
M067R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m067r3.tar.gz"
M067R_REMOTE_EXTRACT_DIR = "/tmp/decodilo-src"
M068R_MILESTONE = "M068R"
M068R_ARMED_FOR = "m068r_dependency_bundle_vertical_slice_single_launch_attempt"
M068R_MANIFEST_COMMAND_LABEL = "m068r-dependency-bundle-command-manifest"
M068R_REMOTE_DEPENDENCY_BUNDLE_PATH = "/tmp/decodilo-dependency-bundle-m068w.tar.gz"
M068R_REMOTE_DEPENDENCY_EXTRACT_DIR = "/tmp/decodilo-deps"
M068R_REMOTE_RUNTIME_TARGET_DIR = "/tmp/decodilo-runtime"
M071R_MILESTONE = "M071R"
M071R_ARMED_FOR = "m071r_first_experiment_single_launch_attempt"
M071R_MANIFEST_COMMAND_LABEL = "m071r-first-experiment-command-manifest"
M071R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-first-experiment-ci-profile-report.json"
M071R_FIRST_EXPERIMENT_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
    "python3",
    "-m",
    "decodilo.cli",
    "dev",
    "ci-profile-report",
    "--out",
    M071R_OUTPUT_ARTIFACT_PATH,
)
M073R_MILESTONE = "M073R"
M073R_ARMED_FOR = "m073r_tiny_smoke_single_launch_attempt"
M073R_MANIFEST_COMMAND_LABEL = "m073r-tiny-smoke-command-manifest"
M073R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m073r.tar.gz"
M073R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-tiny-smoke.json"
M073R_TINY_SMOKE_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
    "python3",
    "-m",
    "decodilo.cli",
    "dev",
    "tiny-smoke",
    "--synthetic",
    "--max-steps",
    "1",
    "--out",
    M073R_OUTPUT_ARTIFACT_PATH,
)
M075R_MILESTONE = "M075R"
M075R_ARMED_FOR = "m075r_runtime_protocol_smoke_single_launch_attempt"
M075R_MANIFEST_COMMAND_LABEL = "m075r-runtime-protocol-smoke-command-manifest"
M075R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m075r.tar.gz"
M075R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-runtime-smoke.json"
M075R_RUNTIME_SMOKE_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
    "python3",
    "-m",
    "decodilo.cli",
    "dev",
    "runtime-smoke",
    "--synthetic",
    "--max-steps",
    "1",
    "--out",
    M075R_OUTPUT_ARTIFACT_PATH,
)
M077R_MILESTONE = "M077R"
M077R_ARMED_FOR = "m077r_first_synthetic_experiment_single_launch_attempt"
M077R_MANIFEST_COMMAND_LABEL = "m077r-first-synthetic-experiment-command-manifest"
M077R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m077r.tar.gz"
M077R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-synthetic-experiment.json"
M077R_SYNTHETIC_EXPERIMENT_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
    "python3",
    "-m",
    "decodilo.cli",
    "dev",
    "synthetic-experiment",
    "--synthetic",
    "--max-steps",
    "1",
    "--out",
    M077R_OUTPUT_ARTIFACT_PATH,
)
M079R_MILESTONE = "M079R"
M079R_ARMED_FOR = "m079r_next_synthetic_experiment_single_launch_attempt"
M079R_MANIFEST_COMMAND_LABEL = "m079r-next-synthetic-experiment-command-manifest"
M079R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m079r.tar.gz"
M079R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-learner-syncer-smoke.json"
M079R_LEARNER_SYNCER_SMOKE_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
    "python3",
    "-m",
    "decodilo.cli",
    "dev",
    "learner-syncer-smoke",
    "--synthetic",
    "--max-steps",
    "1",
    "--out",
    M079R_OUTPUT_ARTIFACT_PATH,
)
M081R_MILESTONE = "M081R"
M081R_ARMED_FOR = "m081r_diloco_synthetic_experiment_single_launch_attempt"
M081R_MANIFEST_COMMAND_LABEL = "m081r-diloco-synthetic-command-manifest"
M081R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m081r.tar.gz"
M081R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-diloco-smoke.json"
M081R_DILOCO_SMOKE_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
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
    M081R_OUTPUT_ARTIFACT_PATH,
)
M083R_MILESTONE = "M083R"
M083R_ARMED_FOR = "m083r_diloco_optimizer_smoke_single_launch_attempt"
M083R_MANIFEST_COMMAND_LABEL = "m083r-diloco-optimizer-command-manifest"
M083R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m083r.tar.gz"
M083R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-diloco-optimizer-smoke.json"
M083R_SELECTED_REGION = "us-west-1"
M083R_DILOCO_OPTIMIZER_SMOKE_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
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
    M083R_OUTPUT_ARTIFACT_PATH,
)
M085R_MILESTONE = "M085R"
M085R_ARMED_FOR = "m085r_integrated_diloco_smoke_single_launch_attempt"
M085R_MANIFEST_COMMAND_LABEL = "m085r-integrated-diloco-command-manifest"
M085R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m085r.tar.gz"
M085R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-integrated-diloco-smoke.json"
M085R_ALLOWED_REGIONS = (M056_SELECTED_REGION, M083R_SELECTED_REGION)
M085R_INTEGRATED_DILOCO_SMOKE_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
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
    M085R_OUTPUT_ARTIFACT_PATH,
)
M087R_MILESTONE = "M087R"
M087R_ARMED_FOR = "m087r_parameter_fragment_smoke_single_launch_attempt"
M087R_MANIFEST_COMMAND_LABEL = "m087r-parameter-fragment-command-manifest"
M087R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m087r.tar.gz"
M087R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-parameter-fragment-smoke.json"
M087R_ALLOWED_REGIONS = M085R_ALLOWED_REGIONS
M087R_PARAMETER_FRAGMENT_SMOKE_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
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
    M087R_OUTPUT_ARTIFACT_PATH,
)
M089R_MILESTONE = "M089R"
M089R_ARMED_FOR = "m089r_bounded_diloco_experiment_single_launch_attempt"
M089R_MANIFEST_COMMAND_LABEL = "m089r-bounded-diloco-experiment-command-manifest"
M089R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m089r.tar.gz"
M089R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-bounded-diloco-experiment.json"
M089R_ALLOWED_REGIONS = M087R_ALLOWED_REGIONS
M089R_BOUNDED_DILOCO_EXPERIMENT_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
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
    M089R_OUTPUT_ARTIFACT_PATH,
)
M093R_MILESTONE = "M093R"
M093R_ARMED_FOR = "m093r_tiny_real_training_smoke_single_launch_attempt"
M093R_MANIFEST_COMMAND_LABEL = "m093r-tiny-real-training-command-manifest"
M093R_REMOTE_BUNDLE_PATH = "/tmp/decodilo-source-bundle-m093r.tar.gz"
M093R_OUTPUT_ARTIFACT_PATH = "/tmp/decodilo-tiny-real-training-smoke.json"
M093R_ALLOWED_REGIONS = M089R_ALLOWED_REGIONS
M093R_TINY_REAL_TRAINING_SMOKE_COMMAND: tuple[str, ...] = (
    "env",
    f"PYTHONPATH={M068R_REMOTE_RUNTIME_TARGET_DIR}:{M067R_REMOTE_EXTRACT_DIR}/src",
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
    M093R_OUTPUT_ARTIFACT_PATH,
)
M067R_IMPORT_PROBE_RELATIVE_PATH = "tools/remote_probe/import_decodilo.py"
M067R_REMOTE_IMPORT_PROBE_PATH = (
    f"{M067R_REMOTE_EXTRACT_DIR}/{M067R_IMPORT_PROBE_RELATIVE_PATH}"
)
M066R_DEFAULT_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("python_version_check", ("python3", "--version")),
    ("decodilo_cli_help_check", ("python3", "-m", "decodilo.cli", "--help")),
    (
        "decodilo_profile_summary_check",
        ("python3", "-m", "decodilo.cli", "dev", "test-profile-summary"),
    ),
)
FORBIDDEN_TOKENS = {
    ";",
    "|",
    ">",
    "<",
    "$(",
    "`",
    "&",
    "&&",
    "||",
    "sh",
    "bash",
    "zsh",
    "fish",
    "nohup",
    "tmux",
    "screen",
    "scp",
    "sftp",
    "rsync",
    "pip",
    "pip3",
    "conda",
    "apt",
    "apt-get",
    "git",
    "clone",
    "docker",
    "curl",
    "wget",
    "download",
    "train",
    "training",
}
M067R_ALLOWED_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("python_version_check", ("python3", "--version")),
    ("source_bundle_hash_check", ("sha256sum", M067R_REMOTE_BUNDLE_PATH)),
    ("source_bundle_extract_dir", ("mkdir", "-p", M067R_REMOTE_EXTRACT_DIR)),
    (
        "source_bundle_extract",
        (
            "tar",
            "-xzf",
            M067R_REMOTE_BUNDLE_PATH,
            "-C",
            M067R_REMOTE_EXTRACT_DIR,
        ),
    ),
    (
        "decodilo_import_check",
        (
            "env",
            f"PYTHONPATH={M067R_REMOTE_EXTRACT_DIR}/src",
            "python3",
            M067R_REMOTE_IMPORT_PROBE_PATH,
        ),
    ),
    (
        "decodilo_cli_help_check",
        (
            "env",
            f"PYTHONPATH={M067R_REMOTE_EXTRACT_DIR}/src",
            "python3",
            "-m",
            "decodilo.cli",
            "--help",
        ),
    ),
    (
        "decodilo_profile_summary_check",
        (
            "env",
            f"PYTHONPATH={M067R_REMOTE_EXTRACT_DIR}/src",
            "python3",
            "-m",
            "decodilo.cli",
            "dev",
            "test-profile-summary",
        ),
    ),
)


def _is_dependency_bundle_milestone(milestone: str) -> bool:
    return milestone in {
        M068R_MILESTONE,
        M071R_MILESTONE,
        M073R_MILESTONE,
        M075R_MILESTONE,
        M077R_MILESTONE,
        M079R_MILESTONE,
        M081R_MILESTONE,
        M083R_MILESTONE,
        M085R_MILESTONE,
        M087R_MILESTONE,
        M089R_MILESTONE,
        M093R_MILESTONE,
    }


def _max_remote_commands_for_milestone(milestone: str) -> int:
    if _is_dependency_bundle_milestone(milestone):
        return 12
    if milestone == M067R_MILESTONE:
        return 8
    return 4


def _upload_policy_for_milestone(milestone: str) -> tuple[int, bool]:
    if _is_dependency_bundle_milestone(milestone):
        return 2, True
    if milestone == M067R_MILESTONE:
        return 1, True
    return 0, False


def _m071r_manifest_contains_exact_experiment_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "first_experiment_command"
        and tuple(entry.argv_tokens) == M071R_FIRST_EXPERIMENT_COMMAND
        for entry in manifest.command_entries
    )


def _m073r_manifest_contains_exact_tiny_smoke_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "tiny_smoke_command"
        and tuple(entry.argv_tokens) == M073R_TINY_SMOKE_COMMAND
        for entry in manifest.command_entries
    )


def _m075r_manifest_contains_exact_runtime_smoke_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "runtime_smoke_command"
        and tuple(entry.argv_tokens) == M075R_RUNTIME_SMOKE_COMMAND
        for entry in manifest.command_entries
    )


def _m077r_manifest_contains_exact_synthetic_experiment_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "synthetic_experiment_command"
        and tuple(entry.argv_tokens) == M077R_SYNTHETIC_EXPERIMENT_COMMAND
        for entry in manifest.command_entries
    )


def _m079r_manifest_contains_exact_learner_syncer_smoke_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "learner_syncer_smoke_command"
        and tuple(entry.argv_tokens) == M079R_LEARNER_SYNCER_SMOKE_COMMAND
        for entry in manifest.command_entries
    )


def _m081r_manifest_contains_exact_diloco_smoke_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "diloco_smoke_command"
        and tuple(entry.argv_tokens) == M081R_DILOCO_SMOKE_COMMAND
        for entry in manifest.command_entries
    )


def _m083r_manifest_contains_exact_diloco_optimizer_smoke_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "diloco_optimizer_smoke_command"
        and tuple(entry.argv_tokens) == M083R_DILOCO_OPTIMIZER_SMOKE_COMMAND
        for entry in manifest.command_entries
    )


def _m085r_manifest_contains_exact_integrated_diloco_smoke_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "integrated_diloco_smoke_command"
        and tuple(entry.argv_tokens) == M085R_INTEGRATED_DILOCO_SMOKE_COMMAND
        for entry in manifest.command_entries
    )


def _m087r_manifest_contains_exact_parameter_fragment_smoke_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "parameter_fragment_smoke_command"
        and tuple(entry.argv_tokens) == M087R_PARAMETER_FRAGMENT_SMOKE_COMMAND
        for entry in manifest.command_entries
    )


def _m089r_manifest_contains_exact_bounded_diloco_experiment_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "bounded_diloco_experiment_command"
        and tuple(entry.argv_tokens) == M089R_BOUNDED_DILOCO_EXPERIMENT_COMMAND
        for entry in manifest.command_entries
    )


def _m093r_manifest_contains_exact_tiny_real_training_smoke_command(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
) -> bool:
    return any(
        entry.stage == "tiny_real_training_smoke_command"
        and tuple(entry.argv_tokens) == M093R_TINY_REAL_TRAINING_SMOKE_COMMAND
        for entry in manifest.command_entries
    )


def _remote_source_bundle_path_for_milestone(milestone: str) -> str:
    if milestone == M093R_MILESTONE:
        return M093R_REMOTE_BUNDLE_PATH
    if milestone == M089R_MILESTONE:
        return M089R_REMOTE_BUNDLE_PATH
    if milestone == M087R_MILESTONE:
        return M087R_REMOTE_BUNDLE_PATH
    if milestone == M085R_MILESTONE:
        return M085R_REMOTE_BUNDLE_PATH
    if milestone == M083R_MILESTONE:
        return M083R_REMOTE_BUNDLE_PATH
    if milestone == M081R_MILESTONE:
        return M081R_REMOTE_BUNDLE_PATH
    if milestone == M079R_MILESTONE:
        return M079R_REMOTE_BUNDLE_PATH
    if milestone == M077R_MILESTONE:
        return M077R_REMOTE_BUNDLE_PATH
    if milestone == M075R_MILESTONE:
        return M075R_REMOTE_BUNDLE_PATH
    if milestone == M073R_MILESTONE:
        return M073R_REMOTE_BUNDLE_PATH
    return M067R_REMOTE_BUNDLE_PATH


def _output_artifact_path_for_milestone(milestone: str) -> str | None:
    if milestone == M071R_MILESTONE:
        return M071R_OUTPUT_ARTIFACT_PATH
    if milestone == M073R_MILESTONE:
        return M073R_OUTPUT_ARTIFACT_PATH
    if milestone == M075R_MILESTONE:
        return M075R_OUTPUT_ARTIFACT_PATH
    if milestone == M077R_MILESTONE:
        return M077R_OUTPUT_ARTIFACT_PATH
    if milestone == M079R_MILESTONE:
        return M079R_OUTPUT_ARTIFACT_PATH
    if milestone == M081R_MILESTONE:
        return M081R_OUTPUT_ARTIFACT_PATH
    if milestone == M083R_MILESTONE:
        return M083R_OUTPUT_ARTIFACT_PATH
    if milestone == M085R_MILESTONE:
        return M085R_OUTPUT_ARTIFACT_PATH
    if milestone == M087R_MILESTONE:
        return M087R_OUTPUT_ARTIFACT_PATH
    if milestone == M089R_MILESTONE:
        return M089R_OUTPUT_ARTIFACT_PATH
    if milestone == M093R_MILESTONE:
        return M093R_OUTPUT_ARTIFACT_PATH
    return None


def _stage_declares_output_artifact_path(
    manifest: LambdaRemoteVerticalSliceCommandManifest,
    *,
    stage: str | None,
    output_artifact_path: str,
) -> bool:
    if stage is None:
        return False
    for entry in manifest.command_entries:
        if entry.stage != stage:
            continue
        tokens = list(entry.argv_tokens)
        return any(
            token == "--out"
            and index + 1 < len(tokens)
            and tokens[index + 1] == output_artifact_path
            for index, token in enumerate(tokens)
        )
    return False
SOURCE_BUNDLE_EXCLUDED_PATTERNS = [
    ".env",
    ".git/",
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".venv/",
    "venv/",
    "node_modules/",
    ".DS_Store",
    "*.pyc",
    "*.pyo",
    "*.pem",
    "*.key",
    "*.ppk",
    "*.pt",
    "*.pth",
    "*.safetensors",
    "*.bin",
    "*.ckpt",
    "*.parquet",
    "*.sqlite",
    "*.db",
]
SECRET_VALUE_REGEXES = {
    "private_key_material": re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----\s+[A-Za-z0-9+/=\s]+-----END [A-Z ]*PRIVATE KEY-----",
        re.MULTILINE,
    ),
    "authorization_bearer_value": re.compile(
        r"Authorization:\s*Bearer\s+(?!<)[A-Za-z0-9._~+/=-]{16,}",
        re.IGNORECASE,
    ),
    "lambda_api_key_value": re.compile(
        r"LAMBDA_API_KEY\s*=\s*(?!<|redacted|REDACTED)[A-Za-z0-9._~+/=-]{16,}",
        re.IGNORECASE,
    ),
    "password_value": re.compile(
        r"password\s*[:=]\s*(?!<|redacted|REDACTED)[A-Za-z0-9._~+/=-]{12,}",
        re.IGNORECASE,
    ),
}
MAX_SOURCE_BUNDLE_FILE_BYTES = 1_250_000


class LambdaRemoteVerticalSlicePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = M066R_MILESTONE
    policy_status: Literal["policy_defined", "blocked"] = "policy_defined"
    max_instances: int = 1
    max_launch_attempts: int = 1
    max_ssh_attempts: int = 1
    max_remote_commands: int = 4
    stop_on_first_failure: bool = True
    ordered_manifest_only: bool = True
    arbitrary_shell_allowed: bool = False
    command_chaining_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    package_install_allowed: bool = False
    downloads_allowed: bool = False
    training_allowed: bool = False
    bounded_output_capture: bool = True
    redacted_output_capture: bool = True
    terminate_owned_instance_required: bool = True
    termination_verification_required: bool = True
    no_auto_retry: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaRemoteVerticalSlicePolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.max_instances != 1
            or self.max_launch_attempts != 1
            or self.max_ssh_attempts != 1
            or self.max_remote_commands > 4
            or not self.stop_on_first_failure
            or not self.ordered_manifest_only
            or self.arbitrary_shell_allowed
            or self.command_chaining_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.package_install_allowed
            or self.downloads_allowed
            or self.training_allowed
            or not self.bounded_output_capture
            or not self.redacted_output_capture
            or not self.terminate_owned_instance_required
            or not self.termination_verification_required
            or not self.no_auto_retry
        ):
            raise ValueError("M066R policy violates remote vertical-slice constraints")
        if self.policy_status == "policy_defined" and self.blockers:
            raise ValueError("defined M066R policy cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def render_lambda_remote_vertical_slice_argv(argv_tokens: list[str] | tuple[str, ...]) -> str:
    """Render structured argv for SSH's single remote-command string."""

    if not argv_tokens or any(
        not isinstance(token, str) or token == "" for token in argv_tokens
    ):
        raise ValueError("remote command argv must contain non-empty string tokens")
    rendered = " ".join(shlex.quote(token) for token in argv_tokens)
    if shlex.split(rendered) != list(argv_tokens):
        raise ValueError("rendered remote command does not round-trip to argv tokens")
    return rendered


class LambdaRemoteVerticalSliceCommandEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage: str
    exact_command: str
    argv_tokens: list[str]
    timeout_seconds: int = Field(default=20, gt=0, le=120)
    allowed_stdout_bytes: int = Field(default=4096, ge=0, le=8192)
    allowed_stderr_bytes: int = Field(default=4096, ge=0, le=8192)
    expected_success_exit_codes: list[int] = Field(default_factory=lambda: [0])
    failure_stage_if_nonzero: str

    @model_validator(mode="after")
    def _validate_entry(self) -> LambdaRemoteVerticalSliceCommandEntry:
        if self.exact_command != render_lambda_remote_vertical_slice_argv(self.argv_tokens):
            raise ValueError("exact_command must equal safe argv renderer output")
        if self.failure_stage_if_nonzero != self.stage:
            raise ValueError("failure stage must match entry stage")
        if not self.argv_tokens or not self.stage:
            raise ValueError("manifest command entry requires stage and argv")
        if len(self.expected_success_exit_codes) != 1 or self.expected_success_exit_codes[0] != 0:
            raise ValueError("M066R only accepts exit code 0 as success")
        return self


class LambdaRemoteVerticalSliceCommandManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_schema_version: int = 1
    milestone: str = M066R_MILESTONE
    stop_on_first_failure: bool = True
    max_remote_commands: int
    command_entries: list[LambdaRemoteVerticalSliceCommandEntry]
    dependency_strategy: str | None = None
    no_internet_install: bool = True
    no_downloads: bool = True
    no_training: bool = True
    forbidden_patterns: list[str] = Field(default_factory=lambda: sorted(FORBIDDEN_TOKENS))
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_manifest_flags(self) -> LambdaRemoteVerticalSliceCommandManifest:
        max_allowed = _max_remote_commands_for_milestone(self.milestone)
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.milestone
            not in {
                M066R_MILESTONE,
                M067R_MILESTONE,
                M068R_MILESTONE,
                M071R_MILESTONE,
                M073R_MILESTONE,
                M075R_MILESTONE,
                M077R_MILESTONE,
                M079R_MILESTONE,
                M081R_MILESTONE,
                M083R_MILESTONE,
                M085R_MILESTONE,
                M087R_MILESTONE,
                M089R_MILESTONE,
                M093R_MILESTONE,
            }
            or not self.stop_on_first_failure
            or self.max_remote_commands != len(self.command_entries)
            or self.max_remote_commands < 1
            or self.max_remote_commands > max_allowed
            or not self.no_internet_install
            or not self.no_downloads
            or not self.no_training
        ):
            raise ValueError("remote vertical-slice manifest violates one-shot constraints")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRemoteVerticalSliceManifestValidation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = M066R_MILESTONE
    validation_passed: bool
    manifest_hash: str
    command_count: int
    stop_on_first_failure: bool
    no_forbidden_tokens: bool
    no_package_install: bool
    no_downloads: bool
    no_file_transfer: bool
    no_port_forwarding: bool
    no_background_processes: bool
    no_arbitrary_shell: bool
    bounded_output_capture: bool
    no_internet_install: bool = True
    dependency_strategy: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaRemoteVerticalSliceManifestValidation:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M066R manifest validation must not enable launch")
        if self.validation_passed and self.blockers:
            raise ValueError("passing M066R manifest validation cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRemoteSourceBundleManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_schema_version: int = 1
    milestone: str = M067R_MILESTONE
    bundle_path: str
    files_included_count: int
    total_bytes: int
    sha256: str
    excluded_patterns: list[str] = Field(default_factory=list)
    included_roots: list[str] = Field(default_factory=list)
    secret_scan_passed: bool
    large_file_scan_passed: bool
    sanitized_symbolic_markers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_bundle_manifest(self) -> LambdaRemoteSourceBundleManifest:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M067R source bundle manifest must not enable launch")
        if len(self.sha256) != 64:
            raise ValueError("source bundle sha256 must be a full hex digest")
        if self.secret_scan_passed and self.large_file_scan_passed and self.blockers:
            raise ValueError("passing source bundle manifest cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRemoteSourceBundleValidation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = M067R_MILESTONE
    validation_passed: bool
    bundle_path: str
    bundle_sha256: str
    files_included_count: int
    total_bytes: int
    secret_scan_passed: bool
    large_file_scan_passed: bool
    bundle_hash_matches_manifest: bool
    max_uploaded_bundles: int = 1
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_bundle_validation(self) -> LambdaRemoteSourceBundleValidation:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.max_uploaded_bundles != 1
        ):
            raise ValueError("M067R source bundle validation violates constraints")
        if self.validation_passed and self.blockers:
            raise ValueError("passing source bundle validation cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRemoteVerticalSliceExecutionPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = M066R_MILESTONE
    ssh_connectivity_path_used: bool = True
    remote_vertical_slice_path_used: bool = True
    plan_status: Literal["plan_passed", "blocked"]
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_candidate_source: str | None = None
    selected_ssh_key_hash: str | None = None
    command_manifest_hash: str
    command_count: int
    command_stages: list[str] = Field(default_factory=list)
    source_bundle_sha256: str | None = None
    source_bundle_path: str | None = None
    dependency_bundle_sha256: str | None = None
    dependency_bundle_path: str | None = None
    dependency_strategy: str | None = None
    declared_artifact_policy_hash: str | None = None
    max_uploaded_bundles: int = 0
    single_source_bundle_upload_allowed: bool = False
    quantity: int = 1
    ssh_username: str = "ubuntu"
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    max_remote_command_attempts: int
    stop_on_first_failure: bool = True
    price_per_instance_hour: float | None = None
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    response_capture_active: bool = True
    status_before_parse: bool = True
    no_auto_launch_retry: bool = True
    strand_payload_compatible: bool = True
    effective_launch_timeout_seconds: float = 30.0
    effective_terminate_timeout_seconds: float = 30.0
    effective_read_only_verification_timeout_seconds: float = 30.0
    ssh_connectivity_only: bool = True
    ssh_attempted: bool = False
    remote_command_attempted: bool = False
    remote_exec_allowed: bool = False
    interactive_shell_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    downloads_allowed: bool = False
    bounded_output_capture: bool = True
    redacted_output_capture: bool = True
    private_key_reference_available_for_probe: bool = True
    old_path_fallback_blocked: bool = True
    m039_path_fallback_blocked: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_plan(self) -> LambdaRemoteVerticalSliceExecutionPlan:
        max_commands = _max_remote_commands_for_milestone(self.milestone)
        expected_uploads, expected_upload_allowed = _upload_policy_for_milestone(
            self.milestone
        )
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.quantity != 1
            or self.max_budget > 50
            or self.max_runtime_minutes > 30
            or self.max_launch_attempts != 1
            or self.max_ssh_connectivity_attempts != 1
            or self.max_remote_command_attempts != self.command_count
            or self.max_remote_command_attempts > max_commands
            or self.max_uploaded_bundles != expected_uploads
            or self.single_source_bundle_upload_allowed != expected_upload_allowed
            or not self.stop_on_first_failure
            or not self.no_auto_launch_retry
            or self.remote_exec_allowed
            or self.interactive_shell_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
            or self.downloads_allowed
            or not self.bounded_output_capture
            or not self.redacted_output_capture
        ):
            raise ValueError("M066R plan violates remote vertical-slice constraints")
        if self.plan_status == "plan_passed" and self.blockers:
            raise ValueError("passing M066R plan cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRemoteVerticalSliceGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = M066R_MILESTONE
    gate_passed: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_ssh_key_hash: str | None = None
    command_manifest_hash: str
    source_bundle_sha256: str | None = None
    dependency_bundle_sha256: str | None = None
    declared_artifact_policy_hash: str | None = None
    max_uploaded_bundles: int = 0
    single_source_bundle_upload_allowed: bool = False
    max_remote_commands: int
    stop_on_first_failure: bool = True
    no_package_install: bool = True
    no_downloads: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_unapproved_training: bool = True
    bounded_output_capture: bool = True
    redacted_output_capture: bool = True
    no_auto_retry: bool = True
    response_capture_active: bool = True
    status_before_parse: bool = True
    effective_launch_timeout_seconds: float = 30.0
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_gate(self) -> LambdaRemoteVerticalSliceGateCheck:
        max_commands = _max_remote_commands_for_milestone(self.milestone)
        expected_uploads, expected_upload_allowed = _upload_policy_for_milestone(
            self.milestone
        )
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.max_remote_commands < 1
            or self.max_remote_commands > max_commands
            or self.max_uploaded_bundles != expected_uploads
            or self.single_source_bundle_upload_allowed != expected_upload_allowed
            or not self.stop_on_first_failure
            or not self.no_package_install
            or not self.no_downloads
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_unapproved_training
            or not self.bounded_output_capture
            or not self.redacted_output_capture
            or not self.no_auto_retry
            or not self.response_capture_active
            or not self.status_before_parse
        ):
            raise ValueError("M066R gate violates remote vertical-slice constraints")
        if self.gate_passed and self.blockers:
            raise ValueError("passing M066R gate cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRemoteVerticalSliceOneShotArming(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    arming_id: str
    arming_status: Literal[
        "not_armed",
        "armed_for_one_shot_m066r_remote_vertical_slice",
        "armed_for_one_shot_m067r_source_bundle_vertical_slice",
        "armed_for_one_shot_m068r_dependency_bundle_vertical_slice",
        "armed_for_one_shot_m071r_first_experiment",
        "armed_for_one_shot_m073r_tiny_smoke",
        "armed_for_one_shot_m075r_runtime_protocol_smoke",
        "armed_for_one_shot_m077r_first_synthetic_experiment",
        "armed_for_one_shot_m079r_next_synthetic_experiment",
        "armed_for_one_shot_m081r_diloco_synthetic_experiment",
        "armed_for_one_shot_m083r_diloco_optimizer_smoke",
        "armed_for_one_shot_m085r_integrated_diloco_smoke",
        "armed_for_one_shot_m087r_parameter_fragment_smoke",
        "armed_for_one_shot_m089r_bounded_diloco_experiment",
        "armed_for_one_shot_m093r_tiny_real_training_smoke",
    ]
    armed_for: str = M066R_ARMED_FOR
    one_shot_request_send_permitted: bool = False
    request_send_permission_delegated_to_reviewer_bridge: bool = True
    selected_candidate: str | None = None
    selected_region: str | None = None
    command_manifest_hash: str
    source_bundle_sha256: str | None = None
    dependency_bundle_sha256: str | None = None
    failure_artifact_capture_policy_hash: str | None = None
    artifact_body_policy_hash: str | None = None
    declared_artifact_policy_hash: str | None = None
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    max_remote_command_attempts: int
    max_uploaded_bundles: int = 0
    single_source_bundle_upload_allowed: bool = False
    stop_on_first_failure: bool = True
    no_auto_retry: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_downloads: bool = True
    no_training: bool = True
    terminate_owned_instance_required: bool = True
    termination_verification_required: bool = True
    created_at_utc: str
    expires_at_utc: str
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_arming(self) -> LambdaRemoteVerticalSliceOneShotArming:
        if self.armed_for == M093R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m093r_tiny_real_training_smoke"
        elif self.armed_for == M089R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m089r_bounded_diloco_experiment"
        elif self.armed_for == M087R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m087r_parameter_fragment_smoke"
        elif self.armed_for == M085R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m085r_integrated_diloco_smoke"
        elif self.armed_for == M083R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m083r_diloco_optimizer_smoke"
        elif self.armed_for == M081R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m081r_diloco_synthetic_experiment"
        elif self.armed_for == M079R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m079r_next_synthetic_experiment"
        elif self.armed_for == M077R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m077r_first_synthetic_experiment"
        elif self.armed_for == M075R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m075r_runtime_protocol_smoke"
        elif self.armed_for == M073R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m073r_tiny_smoke"
        elif self.armed_for == M071R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m071r_first_experiment"
        elif self.armed_for == M068R_ARMED_FOR:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m068r_dependency_bundle_vertical_slice"
        elif self.armed_for == M067R_ARMED_FOR:
            max_commands = 8
            expected_uploads = 1
            expected_upload_allowed = True
            expected_status = "armed_for_one_shot_m067r_source_bundle_vertical_slice"
        else:
            max_commands = 4
            expected_uploads = 0
            expected_upload_allowed = False
            expected_status = "armed_for_one_shot_m066r_remote_vertical_slice"
        if (
            self.armed_for
            not in {
                M066R_ARMED_FOR,
                M067R_ARMED_FOR,
                M068R_ARMED_FOR,
                M071R_ARMED_FOR,
                M073R_ARMED_FOR,
                M075R_ARMED_FOR,
                M077R_ARMED_FOR,
                M079R_ARMED_FOR,
                M081R_ARMED_FOR,
                M083R_ARMED_FOR,
                M085R_ARMED_FOR,
                M087R_ARMED_FOR,
                M089R_ARMED_FOR,
                M093R_ARMED_FOR,
            }
            or self.one_shot_request_send_permitted
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.max_launch_attempts != 1
            or self.max_ssh_connectivity_attempts != 1
            or self.max_remote_command_attempts < 1
            or self.max_remote_command_attempts > max_commands
            or self.max_uploaded_bundles != expected_uploads
            or self.single_source_bundle_upload_allowed != expected_upload_allowed
            or not self.stop_on_first_failure
            or not self.no_auto_retry
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_downloads
            or not self.no_training
            or not self.terminate_owned_instance_required
            or not self.termination_verification_required
        ):
            raise ValueError("M066R arming violates one-shot constraints")
        if self.arming_status == expected_status and self.blockers:
            raise ValueError("armed M066R artifact cannot have blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRemoteVerticalSliceReviewerBridge(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    bridge_status: Literal["not_ready", "reviewer_compatible_one_shot_ready"]
    one_shot_request_send_permitted: bool
    one_shot_ssh_connectivity_probe_permitted: bool
    one_shot_remote_vertical_slice_permitted: bool
    one_shot_minimal_remote_command_permitted: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    command_manifest_hash: str
    source_bundle_sha256: str | None = None
    dependency_bundle_sha256: str | None = None
    failure_artifact_capture_policy_hash: str | None = None
    artifact_body_policy_hash: str | None = None
    declared_artifact_policy_hash: str | None = None
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    max_remote_command_attempts: int
    max_uploaded_bundles: int = 0
    single_source_bundle_upload_allowed: bool = False
    stop_on_first_failure: bool = True
    no_auto_retry: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_downloads: bool = True
    no_training: bool = True
    standing_launch_ready: bool = False
    standing_launch_allowed: bool = False
    expires_at_utc: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_bridge(self) -> LambdaRemoteVerticalSliceReviewerBridge:
        if self.dependency_bundle_sha256 is not None:
            max_commands = 12
            expected_uploads = 2
            expected_upload_allowed = True
        elif self.source_bundle_sha256 is not None:
            max_commands = 8
            expected_uploads = 1
            expected_upload_allowed = True
        else:
            max_commands = 4
            expected_uploads = 0
            expected_upload_allowed = False
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.standing_launch_ready
            or self.standing_launch_allowed
            or self.max_launch_attempts != 1
            or self.max_ssh_connectivity_attempts != 1
            or self.max_remote_command_attempts < 1
            or self.max_remote_command_attempts > max_commands
            or self.max_uploaded_bundles != expected_uploads
            or self.single_source_bundle_upload_allowed != expected_upload_allowed
            or not self.stop_on_first_failure
            or not self.no_auto_retry
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_downloads
            or not self.no_training
        ):
            raise ValueError("M066R bridge violates one-shot constraints")
        if self.bridge_status == "reviewer_compatible_one_shot_ready":
            if (
                self.blockers
                or not self.one_shot_request_send_permitted
                or not self.one_shot_ssh_connectivity_probe_permitted
                or not self.one_shot_remote_vertical_slice_permitted
                or not self.one_shot_minimal_remote_command_permitted
            ):
                raise ValueError("ready M066R bridge requires one-shot permissions")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaRemoteVerticalSliceStageResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    stage: str
    command_hash: str
    exact_command_redacted: str
    exit_code: int | None
    timed_out: bool = False
    stdout_redacted: str | None = None
    stdout_sha256_prefix: str | None = None
    stdout_truncated: bool = False
    stderr_redacted_present: bool = False
    stderr_sha256_prefix: str | None = None
    stderr_truncated: bool = False
    elapsed_seconds: float = 0.0
    passed: bool = False
    failure_stage_if_failed: str | None = None


class LambdaRemoteVerticalSliceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = M066R_MILESTONE
    probe_attempted: bool = False
    probe_completed: bool = False
    probe_passed: bool = False
    auth_result: str = "not_attempted"
    owned_instance_id_redacted: str | None = None
    target_host_redacted: str = "<redacted-host>"
    host_discovery_attempted: bool = False
    host_discovery_status: str | None = None
    host_discovery_source_path: str | None = None
    host_discovery_poll_count: int = 0
    host_discovery_duration_seconds: float = 0.0
    sanitized_metadata_keys: list[str] = Field(default_factory=list)
    sanitized_metadata_key_paths: list[str] = Field(default_factory=list)
    ssh_key_present: bool = False
    ssh_key_permissions_too_open: bool = False
    private_key_reference_redacted: str = "<redacted-private-key-reference>"
    ssh_username: str = "ubuntu"
    ssh_port_readiness_attempted: bool = False
    ssh_port_reachable: bool = False
    ssh_port_poll_count: int = 0
    ssh_port_wait_seconds: float = 0.0
    ssh_port_connect_timeout_seconds: float = 0.0
    ssh_banner_readiness_attempted: bool = False
    ssh_banner_ready: bool = False
    ssh_banner_poll_count: int = 0
    ssh_banner_wait_seconds: float = 0.0
    ssh_banner_read_timeout_seconds: float = 0.0
    ssh_banner_prefix_observed: bool = False
    remote_command_attempted: bool = False
    remote_command_result: str = "not_attempted"
    approved_command: str = M066R_MANIFEST_COMMAND_LABEL
    source_bundle_upload_attempted: bool = False
    source_bundle_upload_succeeded: bool = False
    source_bundle_hash_verified: bool = False
    source_bundle_sha256: str | None = None
    source_bundle_remote_path: str | None = None
    dependency_bundle_upload_attempted: bool = False
    dependency_bundle_upload_succeeded: bool = False
    dependency_bundle_hash_verified: bool = False
    dependency_bundle_sha256: str | None = None
    dependency_bundle_remote_path: str | None = None
    local_dependency_install_attempted: bool = False
    local_dependency_install_succeeded: bool = False
    uploaded_bundles_count: int = 0
    experiment_output_artifact_capture_attempted: bool = False
    experiment_output_artifact_capture_succeeded: bool = False
    experiment_output_artifact_path: str | None = None
    experiment_output_artifact_exists: bool = False
    experiment_output_artifact_bytes: int | None = None
    experiment_output_artifact_sha256: str | None = None
    experiment_output_artifact_secret_scan_passed: bool | None = None
    experiment_output_artifact_body_capture_attempted: bool = False
    experiment_output_artifact_body_capture_succeeded: bool = False
    experiment_output_artifact_body_persisted: bool = False
    experiment_output_artifact_body_json: dict[str, Any] | None = None
    experiment_output_artifact_parsed_summary_persisted: bool = False
    experiment_output_artifact_parsed_summary: dict[str, Any] | None = None
    experiment_output_artifact_parse_status: str | None = None
    experiment_output_artifact_content_capture_status: str | None = None
    command_output_collected: bool = True
    stdout_stored: bool = False
    stdout_capture_active: bool = True
    stdout_redacted: str | None = "<redacted-m066r-stage-output>"
    stdout_sha256_prefix: str | None = None
    stdout_truncated: bool = False
    stdout_secret_scan_passed: bool = True
    stdout_redaction_patterns_applied: list[str] = Field(default_factory=list)
    stderr_capture_active: bool = True
    redacted_stderr_present: bool = False
    stderr_redacted: str | None = None
    stderr_sha256_prefix: str | None = None
    stderr_truncated: bool = False
    stderr_secret_scan_passed: bool = True
    stderr_redaction_patterns_applied: list[str] = Field(default_factory=list)
    ssh_failure_classification: str | None = None
    client_mode: str = "openssh_batch_mode_remote_vertical_slice_manifest"
    bounded_timeout_seconds: int = 20
    exit_status: int | None = None
    elapsed_seconds: float = 0.0
    command_manifest_hash: str
    command_count: int = 0
    commands_executed: int = 0
    stop_on_first_failure: bool = True
    stage_results: list[LambdaRemoteVerticalSliceStageResult] = Field(default_factory=list)
    failed_stage: str | None = None
    vertical_slice_status: str = "not_attempted"
    interactive_shell_attempted: bool = False
    file_transfer_attempted: bool = False
    port_forwarding_attempted: bool = False
    package_install_attempted: bool = False
    training_attempted: bool = False
    downloads_attempted: bool = False
    retry_attempted: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_evidence(self) -> LambdaRemoteVerticalSliceEvidence:
        max_uploads, _ = _upload_policy_for_milestone(self.milestone)
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.approved_command
            not in {
                M066R_MANIFEST_COMMAND_LABEL,
                M067R_MANIFEST_COMMAND_LABEL,
                M068R_MANIFEST_COMMAND_LABEL,
                M071R_MANIFEST_COMMAND_LABEL,
                M073R_MANIFEST_COMMAND_LABEL,
                M075R_MANIFEST_COMMAND_LABEL,
                M077R_MANIFEST_COMMAND_LABEL,
                M079R_MANIFEST_COMMAND_LABEL,
                M081R_MANIFEST_COMMAND_LABEL,
                M083R_MANIFEST_COMMAND_LABEL,
                M085R_MANIFEST_COMMAND_LABEL,
                M087R_MANIFEST_COMMAND_LABEL,
                M089R_MANIFEST_COMMAND_LABEL,
                M093R_MANIFEST_COMMAND_LABEL,
            }
            or self.stdout_stored
            or not self.stdout_secret_scan_passed
            or not self.stderr_capture_active
            or not self.stderr_secret_scan_passed
            or self.interactive_shell_attempted
            or self.file_transfer_attempted
            or self.port_forwarding_attempted
            or self.package_install_attempted
            or self.training_attempted
            or self.downloads_attempted
            or self.retry_attempted
            or (
                self.local_dependency_install_attempted
                and not _is_dependency_bundle_milestone(self.milestone)
            )
            or not self.stop_on_first_failure
            or self.uploaded_bundles_count > max_uploads
        ):
            raise ValueError("M066R evidence violates remote vertical-slice constraints")
        if (
            self.source_bundle_upload_attempted
            and self.milestone == M067R_MILESTONE
            and self.uploaded_bundles_count != 1
        ):
            raise ValueError("M067R source bundle upload must be exactly one bundle")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_remote_vertical_slice_policy() -> LambdaRemoteVerticalSlicePolicy:
    return LambdaRemoteVerticalSlicePolicy(
        warnings=[
            "M066R permits only an exact ordered command manifest",
            "command failure is recorded as a vertical-slice stage result, not a teardown failure",
        ]
    )


def build_lambda_remote_vertical_slice_default_manifest(
    *,
    include_profile_summary: bool = True,
) -> LambdaRemoteVerticalSliceCommandManifest:
    commands = list(
        M066R_DEFAULT_COMMANDS
        if include_profile_summary
        else M066R_DEFAULT_COMMANDS[:2]
    )
    entries = [
        LambdaRemoteVerticalSliceCommandEntry(
            stage=stage,
            exact_command=render_lambda_remote_vertical_slice_argv(argv),
            argv_tokens=list(argv),
            failure_stage_if_nonzero=stage,
        )
        for stage, argv in commands
    ]
    return LambdaRemoteVerticalSliceCommandManifest(
        max_remote_commands=len(entries),
        command_entries=entries,
    )


def build_lambda_remote_source_bundle_default_manifest(
) -> LambdaRemoteVerticalSliceCommandManifest:
    entries = [
        LambdaRemoteVerticalSliceCommandEntry(
            stage=stage,
            exact_command=render_lambda_remote_vertical_slice_argv(argv),
            argv_tokens=list(argv),
            timeout_seconds=30,
            failure_stage_if_nonzero=stage,
        )
        for stage, argv in M067R_ALLOWED_COMMANDS
    ]
    return LambdaRemoteVerticalSliceCommandManifest(
        milestone=M067R_MILESTONE,
        max_remote_commands=len(entries),
        command_entries=entries,
    )


def validate_lambda_remote_vertical_slice_manifest_from_paths(
    *,
    manifest: str | Path,
    policy: str | Path | None = None,
) -> LambdaRemoteVerticalSliceManifestValidation:
    policy_report = (
        load_lambda_remote_vertical_slice_policy(policy)
        if policy is not None
        else build_lambda_remote_vertical_slice_policy()
    )
    try:
        manifest_report = load_lambda_remote_vertical_slice_command_manifest(manifest)
    except Exception as exc:  # noqa: BLE001 - validation reports schema failures.
        return _invalid_remote_vertical_slice_manifest_validation(
            manifest=manifest,
            policy=policy_report,
            error=exc,
        )
    return validate_lambda_remote_vertical_slice_manifest(
        manifest=manifest_report,
        policy=policy_report,
        manifest_path=manifest,
    )


def _invalid_remote_vertical_slice_manifest_validation(
    *,
    manifest: str | Path,
    policy: LambdaRemoteVerticalSlicePolicy,
    error: Exception,
) -> LambdaRemoteVerticalSliceManifestValidation:
    manifest_path = Path(manifest)
    blockers = ["manifest_schema_invalid"]
    milestone = M066R_MILESTONE
    stop_on_first_failure = False
    command_count = 0
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - malformed JSON is the blocker.
        raw = {}
        blockers.append("manifest_json_unreadable")
    if isinstance(raw, dict):
        milestone = raw.get("milestone") or milestone
        stop_on_first_failure = bool(raw.get("stop_on_first_failure"))
        entries = raw.get("command_entries") or []
        command_count = len(entries) if isinstance(entries, list) else 0
        if not isinstance(entries, list):
            blockers.append("manifest_command_entries_must_be_list")
            entries = []
        for index, entry in enumerate(entries):
            text_fragments: list[str] = []
            if isinstance(entry, str):
                blockers.append(f"raw_shell_string_command_entry_{index}")
                text_fragments.append(entry)
            elif isinstance(entry, dict):
                argv = entry.get("argv_tokens")
                exact = entry.get("exact_command")
                command = entry.get("command")
                if isinstance(command, str):
                    blockers.append(f"raw_shell_command_string_in_entry_{index}")
                    text_fragments.append(command)
                if not isinstance(argv, list) or not all(
                    isinstance(token, str) for token in argv
                ):
                    blockers.append(f"argv_tokens_required_in_entry_{index}")
                else:
                    text_fragments.extend(argv)
                if isinstance(exact, str):
                    text_fragments.append(exact)
            else:
                blockers.append(f"manifest_command_entry_{index}_must_be_object")
            text = " ".join(text_fragments)
            if "python3 -c" in text or "python -c" in text or " -c " in text:
                blockers.append(f"forbidden_python_inline_code_in_entry_{index}")
            if any(pattern in text for pattern in (";", "|", ">", "<", "$(", "`", "&")):
                blockers.append(f"forbidden_shell_metacharacter_in_entry_{index}")
    else:
        blockers.append("manifest_root_must_be_object")
    if policy.policy_status != "policy_defined":
        blockers.extend(policy.blockers or ["m066r_policy_not_defined"])
    return LambdaRemoteVerticalSliceManifestValidation(
        milestone=milestone,
        validation_passed=False,
        manifest_hash=_sha256_file(manifest_path) if manifest_path.exists() else "0" * 64,
        command_count=command_count,
        stop_on_first_failure=stop_on_first_failure,
        no_forbidden_tokens=not any(
            blocker.startswith("forbidden_") for blocker in blockers
        ),
        no_package_install=not any("package_install" in blocker for blocker in blockers),
        no_downloads=not any("download" in blocker for blocker in blockers),
        no_file_transfer=not any("file_transfer" in blocker for blocker in blockers),
        no_port_forwarding=not any("port_forwarding" in blocker for blocker in blockers),
        no_background_processes=not any("background" in blocker for blocker in blockers),
        no_arbitrary_shell=not any("shell" in blocker for blocker in blockers),
        bounded_output_capture=False,
        no_internet_install=False,
        dependency_strategy=None,
        blockers=sorted({*blockers, f"manifest_schema_error:{type(error).__name__}"}),
        warnings=["manifest is rejected before execution"],
    )


def validate_lambda_remote_vertical_slice_manifest(
    *,
    manifest: LambdaRemoteVerticalSliceCommandManifest,
    policy: LambdaRemoteVerticalSlicePolicy,
    manifest_path: str | Path | None = None,
) -> LambdaRemoteVerticalSliceManifestValidation:
    blockers: list[str] = []
    if policy.policy_status != "policy_defined":
        blockers.extend(policy.blockers or ["m066r_policy_not_defined"])
    if not manifest.stop_on_first_failure:
        blockers.append("manifest_must_stop_on_first_failure")
    max_allowed_commands = (
        12
        if _is_dependency_bundle_milestone(manifest.milestone)
        else 8
        if manifest.milestone == M067R_MILESTONE
        else policy.max_remote_commands
    )
    if manifest.max_remote_commands > max_allowed_commands:
        blockers.append("manifest_exceeds_policy_command_limit")
    stages = [entry.stage for entry in manifest.command_entries]
    if len(stages) != len(set(stages)):
        blockers.append("manifest_stages_must_be_unique")
    for entry in manifest.command_entries:
        blockers.extend(_validate_command_entry(entry, milestone=manifest.milestone))
    no_forbidden = not any(blocker.startswith("forbidden_") for blocker in blockers)
    no_install = not any("package_install" in blocker for blocker in blockers)
    no_downloads = not any("download" in blocker for blocker in blockers)
    no_transfer = not any("file_transfer" in blocker for blocker in blockers)
    no_forward = not any("port_forwarding" in blocker for blocker in blockers)
    no_background = not any("background" in blocker for blocker in blockers)
    no_shell = not any("shell" in blocker for blocker in blockers)
    return LambdaRemoteVerticalSliceManifestValidation(
        milestone=manifest.milestone,
        validation_passed=not blockers,
        manifest_hash=(
            _sha256_file(manifest_path)
            if manifest_path
            else _hash_json(manifest.model_dump(mode="json"))
        ),
        command_count=len(manifest.command_entries),
        stop_on_first_failure=manifest.stop_on_first_failure,
        no_forbidden_tokens=no_forbidden,
        no_package_install=no_install,
        no_downloads=no_downloads,
        no_file_transfer=no_transfer,
        no_port_forwarding=no_forward,
        no_background_processes=no_background,
        no_arbitrary_shell=no_shell,
        bounded_output_capture=all(
            entry.allowed_stdout_bytes <= 8192 and entry.allowed_stderr_bytes <= 8192
            for entry in manifest.command_entries
        ),
        no_internet_install=manifest.no_internet_install,
        dependency_strategy=manifest.dependency_strategy,
        blockers=sorted(set(blockers)),
        warnings=[
            "manifest is non-executable by itself",
            "M066R will stop at the first nonzero exit or timeout",
        ],
    )


def build_lambda_remote_source_bundle(
    *,
    project_root: str | Path,
    bundle: str | Path,
    manifest_out: str | Path,
) -> LambdaRemoteSourceBundleManifest:
    root = Path(project_root).resolve()
    bundle_path = Path(bundle)
    manifest_path = Path(manifest_out)
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    files, blockers, warnings = _collect_source_bundle_files(root)
    secret_scan_passed = not any(blocker.startswith("secret_") for blocker in blockers)
    large_file_scan_passed = not any(blocker.startswith("large_file_") for blocker in blockers)
    if blockers:
        report = LambdaRemoteSourceBundleManifest(
            bundle_path=str(bundle_path),
            files_included_count=len(files),
            total_bytes=sum(path.stat().st_size for path in files if path.exists()),
            sha256="0" * 64,
            excluded_patterns=SOURCE_BUNDLE_EXCLUDED_PATTERNS,
            included_roots=["src", "pyproject.toml", "tools/remote_probe"],
            secret_scan_passed=secret_scan_passed,
            large_file_scan_passed=large_file_scan_passed,
            blockers=sorted(set(blockers)),
            warnings=warnings,
        )
        write_lambda_remote_source_bundle_manifest(manifest_path, report)
        return report
    if bundle_path.exists():
        bundle_path.unlink()
    with tarfile.open(bundle_path, "w:gz") as tar:
        for file_path in files:
            tar.add(file_path, arcname=str(file_path.relative_to(root)))
    sha = _sha256_file(bundle_path)
    report = LambdaRemoteSourceBundleManifest(
        bundle_path=str(bundle_path),
        files_included_count=len(files),
        total_bytes=sum(path.stat().st_size for path in files),
        sha256=sha,
        excluded_patterns=SOURCE_BUNDLE_EXCLUDED_PATTERNS,
        included_roots=["src", "pyproject.toml", "tools/remote_probe"],
        secret_scan_passed=True,
        large_file_scan_passed=True,
        sanitized_symbolic_markers=[
            "symbolic credential references in source are allowed only when no value is present"
        ],
        warnings=[
            "bundle excludes tests, README, VCS metadata, caches, env files, and artifacts",
            *warnings,
        ],
    )
    write_lambda_remote_source_bundle_manifest(manifest_path, report)
    return report


def validate_lambda_remote_source_bundle_from_paths(
    *,
    bundle: str | Path,
    manifest: str | Path,
) -> LambdaRemoteSourceBundleValidation:
    manifest_report = load_lambda_remote_source_bundle_manifest(manifest)
    blockers: list[str] = list(manifest_report.blockers)
    bundle_path = Path(bundle)
    if not bundle_path.is_file():
        blockers.append("source_bundle_missing")
        actual_sha = "0" * 64
    else:
        actual_sha = _sha256_file(bundle_path)
    if actual_sha != manifest_report.sha256:
        blockers.append("source_bundle_hash_mismatch")
    if not manifest_report.secret_scan_passed:
        blockers.append("source_bundle_secret_scan_failed")
    if not manifest_report.large_file_scan_passed:
        blockers.append("source_bundle_large_file_scan_failed")
    if str(bundle_path) != manifest_report.bundle_path:
        blockers.append("source_bundle_path_mismatch")
    if bundle_path.is_file():
        try:
            with tarfile.open(bundle_path, "r:gz") as tar:
                members = tar.getmembers()
                names = [member.name for member in members]
                if any(_bundle_member_forbidden(name) for name in names):
                    blockers.append("source_bundle_contains_forbidden_path")
                if any(member.size > MAX_SOURCE_BUNDLE_FILE_BYTES for member in members):
                    blockers.append("source_bundle_contains_large_file")
        except tarfile.TarError:
            blockers.append("source_bundle_tar_unreadable")
    return LambdaRemoteSourceBundleValidation(
        validation_passed=not blockers,
        bundle_path=str(bundle_path),
        bundle_sha256=actual_sha,
        files_included_count=manifest_report.files_included_count,
        total_bytes=manifest_report.total_bytes,
        secret_scan_passed=manifest_report.secret_scan_passed,
        large_file_scan_passed=manifest_report.large_file_scan_passed,
        bundle_hash_matches_manifest=actual_sha == manifest_report.sha256,
        blockers=sorted(set(blockers)),
        warnings=[
            "source bundle validation is local-only and non-launching",
            *manifest_report.warnings,
        ],
    )


def build_lambda_remote_vertical_slice_execution_plan_from_paths(
    *,
    discovery_report: str | Path,
    manifest: str | Path,
    manifest_validation: str | Path,
    ssh_key_selection: str | Path,
    price_snapshot: str | Path,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaRemoteVerticalSliceExecutionPlan:
    return build_lambda_remote_vertical_slice_execution_plan(
        discovery=load_lambda_live_discovery_report(discovery_report),
        manifest=load_lambda_remote_vertical_slice_command_manifest(manifest),
        manifest_validation=load_lambda_remote_vertical_slice_manifest_validation(
            manifest_validation
        ),
        ssh_key_selection_path=ssh_key_selection,
        price_snapshot=load_price_snapshot(price_snapshot),
        max_budget=max_budget,
        planned_runtime_minutes=planned_runtime_minutes,
        safety_buffer_multiplier=safety_buffer_multiplier,
    )


def build_lambda_remote_vertical_slice_execution_plan(
    *,
    discovery: LambdaLiveDiscoveryReport,
    manifest: LambdaRemoteVerticalSliceCommandManifest,
    manifest_validation: LambdaRemoteVerticalSliceManifestValidation,
    ssh_key_selection_path: str | Path,
    price_snapshot: PriceSnapshot,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaRemoteVerticalSliceExecutionPlan:
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection_path)
    blockers: list[str] = []
    if not manifest_validation.validation_passed:
        blockers.extend(manifest_validation.blockers or ["manifest_validation_failed"])
    if not discovery.live_api_used or not discovery.read_only_mode:
        blockers.append("fresh_live_read_only_discovery_required")
    if not discovery.required_endpoint_success:
        blockers.append("required_read_only_endpoint_failed")
    if discovery.summary.read_operations <= 0:
        blockers.append("read_only_discovery_must_have_read_operations")
    if discovery.summary.mutating_operations != 0:
        blockers.append("read_only_discovery_report_contains_mutation")
    if discovery.billable_action_performed:
        blockers.append("read_only_discovery_cannot_be_billable")
    if discovery.unmanaged_instances:
        blockers.append("unmanaged_instances_present")
    if price_snapshot.is_sample_data:
        blockers.append("non_sample_price_snapshot_required")
    if not ssh.selection_passed:
        blockers.extend(ssh.errors or ["existing_ssh_key_selection_required"])
    if not ssh.selected_ssh_key_name_for_payload:
        blockers.append("raw_existing_ssh_key_name_missing_from_private_artifact")
    if ssh.raw_public_key_material_present:
        blockers.append("raw_public_key_material_present")
    selected = _select_candidate(
        discovery,
        price_snapshot,
        max_budget,
        planned_runtime_minutes,
        safety_buffer_multiplier,
    )
    if selected is None:
        blockers.append("no_safe_live_candidate_under_budget")
        selected_shape = selected_region = selected_source = None
        selected_gpu_type = None
        selected_gpus = None
        price_per_hour = estimated = buffered = None
    else:
        (
            selected_shape,
            selected_region,
            selected_source,
            selected_gpu_type,
            selected_gpus,
            price_per_hour,
            estimated,
            buffered,
        ) = selected
        if buffered is not None and buffered >= max_budget:
            blockers.append("buffered_estimated_cost_not_below_max_budget")
    return LambdaRemoteVerticalSliceExecutionPlan(
        plan_status="plan_passed" if not blockers else "blocked",
        selected_candidate=selected_shape,
        selected_region=selected_region,
        selected_candidate_source=selected_source,
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash,
        command_manifest_hash=manifest_validation.manifest_hash,
        command_count=len(manifest.command_entries),
        command_stages=[entry.stage for entry in manifest.command_entries],
        max_budget=max_budget,
        max_runtime_minutes=planned_runtime_minutes,
        max_remote_command_attempts=len(manifest.command_entries),
        price_per_instance_hour=price_per_hour,
        gpu_type=selected_gpu_type,
        gpus_per_instance=selected_gpus,
        estimated_30min_cost=estimated,
        buffered_estimated_30min_cost=buffered,
        blockers=sorted(set(blockers)),
        warnings=[
            "M066R plan is non-executable until one-shot reviewer bridge is valid",
            "candidate and region came from fresh read-only discovery",
            "command manifest is bounded and fail-fast",
        ],
    )


def build_lambda_remote_source_bundle_execution_plan_from_paths(
    *,
    discovery_report: str | Path,
    source_bundle_validation: str | Path,
    command_manifest: str | Path,
    manifest_validation: str | Path,
    ssh_key_selection: str | Path,
    price_snapshot: str | Path,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaRemoteVerticalSliceExecutionPlan:
    discovery = load_lambda_live_discovery_report(discovery_report)
    bundle_validation = load_lambda_remote_source_bundle_validation(
        source_bundle_validation
    )
    manifest = load_lambda_remote_vertical_slice_command_manifest(command_manifest)
    validation = load_lambda_remote_vertical_slice_manifest_validation(
        manifest_validation
    )
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    price = load_price_snapshot(price_snapshot)
    blockers: list[str] = []
    if not bundle_validation.validation_passed:
        blockers.extend(bundle_validation.blockers or ["source_bundle_validation_failed"])
    if manifest.milestone != M067R_MILESTONE:
        blockers.append("m067r_manifest_required")
    if validation.milestone != M067R_MILESTONE:
        blockers.append("m067r_manifest_validation_required")
    if not validation.validation_passed:
        blockers.extend(validation.blockers or ["manifest_validation_failed"])
    if validation.command_count > 8:
        blockers.append("manifest_exceeds_m067r_command_limit")
    if not discovery.live_api_used or not discovery.read_only_mode:
        blockers.append("fresh_live_read_only_discovery_required")
    if not discovery.required_endpoint_success:
        blockers.append("required_read_only_endpoint_failed")
    if discovery.summary.read_operations <= 0:
        blockers.append("read_only_discovery_must_have_read_operations")
    if discovery.summary.mutating_operations != 0:
        blockers.append("read_only_discovery_report_contains_mutation")
    if discovery.billable_action_performed:
        blockers.append("read_only_discovery_cannot_be_billable")
    if discovery.unmanaged_instances:
        blockers.append("unmanaged_instances_present")
    if price.is_sample_data:
        blockers.append("non_sample_price_snapshot_required")
    if not ssh.selection_passed:
        blockers.extend(ssh.errors or ["existing_ssh_key_selection_required"])
    if not ssh.selected_ssh_key_name_for_payload:
        blockers.append("raw_existing_ssh_key_name_missing_from_private_artifact")
    if ssh.raw_public_key_material_present:
        blockers.append("raw_public_key_material_present")
    selected = _select_candidate(
        discovery,
        price,
        max_budget,
        planned_runtime_minutes,
        safety_buffer_multiplier,
    )
    if selected is None:
        blockers.append("no_safe_live_candidate_under_budget")
        selected_shape = selected_region = selected_source = None
        selected_gpu_type = None
        selected_gpus = None
        price_per_hour = estimated = buffered = None
    else:
        (
            selected_shape,
            selected_region,
            selected_source,
            selected_gpu_type,
            selected_gpus,
            price_per_hour,
            estimated,
            buffered,
        ) = selected
    return LambdaRemoteVerticalSliceExecutionPlan(
        milestone=M067R_MILESTONE,
        remote_vertical_slice_path_used=True,
        plan_status="plan_passed" if not blockers else "blocked",
        selected_candidate=selected_shape,
        selected_region=selected_region,
        selected_candidate_source=selected_source,
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash,
        command_manifest_hash=validation.manifest_hash,
        command_count=len(manifest.command_entries),
        command_stages=[entry.stage for entry in manifest.command_entries],
        source_bundle_sha256=bundle_validation.bundle_sha256,
        source_bundle_path=bundle_validation.bundle_path,
        max_uploaded_bundles=1,
        single_source_bundle_upload_allowed=True,
        max_budget=max_budget,
        max_runtime_minutes=planned_runtime_minutes,
        max_remote_command_attempts=len(manifest.command_entries),
        price_per_instance_hour=price_per_hour,
        gpu_type=selected_gpu_type,
        gpus_per_instance=selected_gpus,
        estimated_30min_cost=estimated,
        buffered_estimated_30min_cost=buffered,
        blockers=sorted(set(blockers)),
        warnings=[
            "M067R plan permits one sanitized source bundle upload only",
            "candidate and region came from fresh read-only discovery",
            "command manifest is bounded and fail-fast",
        ],
    )


def build_lambda_remote_dependency_bundle_execution_plan_from_paths(
    *,
    discovery_report: str | Path,
    source_bundle_validation: str | Path,
    dependency_bundle_validation: str | Path,
    command_manifest: str | Path,
    manifest_validation: str | Path,
    ssh_key_selection: str | Path,
    price_snapshot: str | Path,
    max_budget: float = 50.0,
    planned_runtime_minutes: int = 30,
    safety_buffer_multiplier: float = 1.15,
) -> LambdaRemoteVerticalSliceExecutionPlan:
    from decodilo.lambda_cloud.remote_dependency_bundle import (
        load_lambda_dependency_bundle_validation,
    )

    discovery = load_lambda_live_discovery_report(discovery_report)
    source_validation = load_lambda_remote_source_bundle_validation(
        source_bundle_validation
    )
    dependency_validation = load_lambda_dependency_bundle_validation(
        dependency_bundle_validation
    )
    manifest = load_lambda_remote_vertical_slice_command_manifest(command_manifest)
    validation = load_lambda_remote_vertical_slice_manifest_validation(
        manifest_validation
    )
    ssh = load_lambda_existing_ssh_key_selection(ssh_key_selection)
    price = load_price_snapshot(price_snapshot)
    blockers: list[str] = []
    if not source_validation.validation_passed:
        blockers.extend(source_validation.blockers or ["source_bundle_validation_failed"])
    if not dependency_validation.validation_passed:
        blockers.extend(
            dependency_validation.blockers or ["dependency_bundle_validation_failed"]
        )
    if manifest.milestone not in {
        M068R_MILESTONE,
        M071R_MILESTONE,
        M073R_MILESTONE,
        M075R_MILESTONE,
        M077R_MILESTONE,
        M079R_MILESTONE,
        M081R_MILESTONE,
        M083R_MILESTONE,
        M085R_MILESTONE,
        M087R_MILESTONE,
        M089R_MILESTONE,
        M093R_MILESTONE,
    }:
        blockers.append("dependency_bundle_manifest_required")
    if validation.milestone != manifest.milestone:
        blockers.append("dependency_bundle_manifest_validation_milestone_mismatch")
    if (
        manifest.milestone == M071R_MILESTONE
        and not _m071r_manifest_contains_exact_experiment_command(manifest)
    ):
        blockers.append("m071r_exact_first_experiment_command_required")
    if (
        manifest.milestone == M073R_MILESTONE
        and not _m073r_manifest_contains_exact_tiny_smoke_command(manifest)
    ):
        blockers.append("m073r_exact_tiny_smoke_command_required")
    if (
        manifest.milestone == M075R_MILESTONE
        and not _m075r_manifest_contains_exact_runtime_smoke_command(manifest)
    ):
        blockers.append("m075r_exact_runtime_smoke_command_required")
    if (
        manifest.milestone == M077R_MILESTONE
        and not _m077r_manifest_contains_exact_synthetic_experiment_command(manifest)
    ):
        blockers.append("m077r_exact_synthetic_experiment_command_required")
    if (
        manifest.milestone == M079R_MILESTONE
        and not _m079r_manifest_contains_exact_learner_syncer_smoke_command(manifest)
    ):
        blockers.append("m079r_exact_learner_syncer_smoke_command_required")
    if (
        manifest.milestone == M081R_MILESTONE
        and not _m081r_manifest_contains_exact_diloco_smoke_command(manifest)
    ):
        blockers.append("m081r_exact_diloco_smoke_command_required")
    if (
        manifest.milestone == M083R_MILESTONE
        and not _m083r_manifest_contains_exact_diloco_optimizer_smoke_command(manifest)
    ):
        blockers.append("m083r_exact_diloco_optimizer_smoke_command_required")
    if (
        manifest.milestone == M085R_MILESTONE
        and not _m085r_manifest_contains_exact_integrated_diloco_smoke_command(manifest)
    ):
        blockers.append("m085r_exact_integrated_diloco_smoke_command_required")
    if (
        manifest.milestone == M087R_MILESTONE
        and not _m087r_manifest_contains_exact_parameter_fragment_smoke_command(manifest)
    ):
        blockers.append("m087r_exact_parameter_fragment_smoke_command_required")
    if (
        manifest.milestone == M089R_MILESTONE
        and not _m089r_manifest_contains_exact_bounded_diloco_experiment_command(
            manifest
        )
    ):
        blockers.append("m089r_exact_bounded_diloco_experiment_command_required")
    if (
        manifest.milestone == M093R_MILESTONE
        and not _m093r_manifest_contains_exact_tiny_real_training_smoke_command(
            manifest
        )
    ):
        blockers.append("m093r_exact_tiny_real_training_smoke_command_required")
    if not validation.validation_passed:
        blockers.extend(validation.blockers or ["manifest_validation_failed"])
    if validation.command_count > 12:
        blockers.append("manifest_exceeds_dependency_bundle_command_limit")
    if manifest.max_remote_commands != validation.command_count:
        blockers.append("manifest_validation_command_count_mismatch")
    if not manifest.no_internet_install or not validation.no_internet_install:
        blockers.append("no_internet_install_required")
    if not dependency_validation.secret_scan_passed:
        blockers.append("dependency_bundle_secret_scan_failed")
    if dependency_validation.internet_download_used and (
        dependency_validation.dependency_strategy != "local_wheelhouse"
    ):
        blockers.append("dependency_bundle_internet_download_not_allowed")
    if not discovery.live_api_used or not discovery.read_only_mode:
        blockers.append("fresh_live_read_only_discovery_required")
    if not discovery.required_endpoint_success:
        blockers.append("required_read_only_endpoint_failed")
    if discovery.summary.read_operations <= 0:
        blockers.append("read_only_discovery_must_have_read_operations")
    if discovery.summary.mutating_operations != 0:
        blockers.append("read_only_discovery_report_contains_mutation")
    if discovery.billable_action_performed:
        blockers.append("read_only_discovery_cannot_be_billable")
    if discovery.unmanaged_instances:
        blockers.append("unmanaged_instances_present")
    if price.is_sample_data:
        blockers.append("non_sample_price_snapshot_required")
    if not ssh.selection_passed:
        blockers.extend(ssh.errors or ["existing_ssh_key_selection_required"])
    if not ssh.selected_ssh_key_name_for_payload:
        blockers.append("raw_existing_ssh_key_name_missing_from_private_artifact")
    if ssh.raw_public_key_material_present:
        blockers.append("raw_public_key_material_present")
    selected = _select_candidate(
        discovery,
        price,
        max_budget,
        planned_runtime_minutes,
        safety_buffer_multiplier,
    )
    if selected is None:
        blockers.append("no_safe_live_candidate_under_budget")
        selected_shape = selected_region = selected_source = None
        selected_gpu_type = None
        selected_gpus = None
        price_per_hour = estimated = buffered = None
    else:
        (
            selected_shape,
            selected_region,
            selected_source,
            selected_gpu_type,
            selected_gpus,
            price_per_hour,
            estimated,
            buffered,
        ) = selected
    required_region = (
        M083R_SELECTED_REGION
        if manifest.milestone == M083R_MILESTONE
        else M056_SELECTED_REGION
    )
    if manifest.milestone in {
        M085R_MILESTONE,
        M087R_MILESTONE,
        M089R_MILESTONE,
        M093R_MILESTONE,
    }:
        if (
            selected_shape != M056_SELECTED_CANDIDATE
            or selected_region
            not in (
                M093R_ALLOWED_REGIONS
                if manifest.milestone == M093R_MILESTONE
                else
                M089R_ALLOWED_REGIONS
                if manifest.milestone == M089R_MILESTONE
                else
                M087R_ALLOWED_REGIONS
                if manifest.milestone == M087R_MILESTONE
                else M085R_ALLOWED_REGIONS
            )
        ):
            blockers.append("known_ssh_ready_candidate_not_live")
    elif manifest.milestone in {
        M071R_MILESTONE,
        M073R_MILESTONE,
        M075R_MILESTONE,
        M077R_MILESTONE,
        M079R_MILESTONE,
        M081R_MILESTONE,
        M083R_MILESTONE,
    } and (selected_shape != M056_SELECTED_CANDIDATE or selected_region != required_region):
        blockers.append("known_ssh_ready_candidate_not_live")
    return LambdaRemoteVerticalSliceExecutionPlan(
        milestone=manifest.milestone,
        remote_vertical_slice_path_used=True,
        plan_status="plan_passed" if not blockers else "blocked",
        selected_candidate=selected_shape,
        selected_region=selected_region,
        selected_candidate_source=selected_source,
        selected_ssh_key_hash=ssh.selected_ssh_key_name_redacted_or_hash,
        command_manifest_hash=validation.manifest_hash,
        command_count=len(manifest.command_entries),
        command_stages=[entry.stage for entry in manifest.command_entries],
        source_bundle_sha256=source_validation.bundle_sha256,
        source_bundle_path=source_validation.bundle_path,
        dependency_bundle_sha256=dependency_validation.bundle_sha256,
        dependency_bundle_path=dependency_validation.bundle_path,
        dependency_strategy=dependency_validation.dependency_strategy,
        max_uploaded_bundles=2,
        single_source_bundle_upload_allowed=True,
        max_budget=max_budget,
        max_runtime_minutes=planned_runtime_minutes,
        max_remote_command_attempts=len(manifest.command_entries),
        price_per_instance_hour=price_per_hour,
        gpu_type=selected_gpu_type,
        gpus_per_instance=selected_gpus,
        estimated_30min_cost=estimated,
        buffered_estimated_30min_cost=buffered,
        blockers=sorted(set(blockers)),
        warnings=[
            (
                "M089R plan permits one complete bounded synthetic DiLoCo "
                "experiment command after bounded setup"
                if manifest.milestone == M089R_MILESTONE
                else (
                "M093R plan permits one tiny real-training smoke command "
                "after bounded setup"
                )
                if manifest.milestone == M093R_MILESTONE
                else (
                "M087R plan permits one bounded parameter-fragment smoke command "
                "after bounded setup"
                )
                if manifest.milestone == M087R_MILESTONE
                else (
                "M083R plan permits one bounded optimizer-fidelity smoke command "
                "after bounded setup"
                )
                if manifest.milestone == M083R_MILESTONE
                else (
                    "M085R plan permits one bounded integrated DiLoCo smoke command "
                    "after bounded setup"
                )
                if manifest.milestone == M085R_MILESTONE
                else (
                    "M081R plan permits one bounded DiLoCo-shaped synthetic command "
                    "after bounded setup"
                )
                if manifest.milestone == M081R_MILESTONE
                else (
                    "M079R plan permits one bounded learner/syncer smoke command "
                    "after bounded setup"
                )
                if manifest.milestone == M079R_MILESTONE
                else (
                    "M077R plan permits one bounded synthetic experiment command "
                    "after bounded setup"
                )
                if manifest.milestone == M077R_MILESTONE
                else "M075R plan permits one runtime/protocol smoke command after bounded setup"
                if manifest.milestone == M075R_MILESTONE
                else "M073R plan permits one tiny-smoke command after bounded setup"
                if manifest.milestone == M073R_MILESTONE
                else "M071R plan permits one first-experiment command after bounded setup"
                if manifest.milestone == M071R_MILESTONE
                else "M068R plan permits one source bundle and one dependency wheelhouse upload"
            ),
            "candidate and region came from fresh read-only discovery",
            "dependency install must use local wheelhouse with --no-index",
        ],
    )


def build_lambda_remote_vertical_slice_gate_check_from_paths(
    *,
    plan: str | Path,
    policy: str | Path,
    manifest_validation: str | Path,
) -> LambdaRemoteVerticalSliceGateCheck:
    plan_report = load_lambda_remote_vertical_slice_execution_plan(plan)
    policy_report = load_lambda_remote_vertical_slice_policy(policy)
    validation = load_lambda_remote_vertical_slice_manifest_validation(
        manifest_validation
    )
    blockers = [*plan_report.blockers, *validation.blockers, *policy_report.blockers]
    if plan_report.plan_status != "plan_passed":
        blockers.append("m066r_plan_not_passed")
    if policy_report.policy_status != "policy_defined":
        blockers.append("m066r_policy_not_defined")
    if not validation.validation_passed:
        blockers.append("m066r_manifest_validation_not_passed")
    if validation.manifest_hash != plan_report.command_manifest_hash:
        blockers.append("m066r_manifest_hash_mismatch")
    return LambdaRemoteVerticalSliceGateCheck(
        gate_passed=not blockers,
        selected_candidate=plan_report.selected_candidate,
        selected_region=plan_report.selected_region,
        selected_ssh_key_hash=plan_report.selected_ssh_key_hash,
        command_manifest_hash=plan_report.command_manifest_hash,
        max_remote_commands=plan_report.max_remote_command_attempts,
        response_capture_active=plan_report.response_capture_active,
        status_before_parse=plan_report.status_before_parse,
        effective_launch_timeout_seconds=plan_report.effective_launch_timeout_seconds,
        blockers=sorted(set(blockers)),
        warnings=[
            "M066R gate allows only manifest-bound fail-fast Decodilo vertical slice",
        ],
    )


def build_lambda_remote_source_bundle_gate_check_from_paths(
    *,
    plan: str | Path,
) -> LambdaRemoteVerticalSliceGateCheck:
    plan_report = load_lambda_remote_vertical_slice_execution_plan(plan)
    blockers = list(plan_report.blockers)
    if plan_report.milestone != M067R_MILESTONE:
        blockers.append("m067r_plan_required")
    if plan_report.plan_status != "plan_passed":
        blockers.append("m067r_plan_not_passed")
    if not plan_report.source_bundle_sha256:
        blockers.append("source_bundle_sha256_required")
    if plan_report.max_uploaded_bundles != 1:
        blockers.append("exactly_one_source_bundle_upload_required")
    if not plan_report.single_source_bundle_upload_allowed:
        blockers.append("single_source_bundle_upload_not_allowed")
    return LambdaRemoteVerticalSliceGateCheck(
        milestone=M067R_MILESTONE,
        gate_passed=not blockers,
        selected_candidate=plan_report.selected_candidate,
        selected_region=plan_report.selected_region,
        selected_ssh_key_hash=plan_report.selected_ssh_key_hash,
        command_manifest_hash=plan_report.command_manifest_hash,
        source_bundle_sha256=plan_report.source_bundle_sha256,
        max_uploaded_bundles=1,
        single_source_bundle_upload_allowed=True,
        max_remote_commands=plan_report.max_remote_command_attempts,
        response_capture_active=plan_report.response_capture_active,
        status_before_parse=plan_report.status_before_parse,
        effective_launch_timeout_seconds=plan_report.effective_launch_timeout_seconds,
        blockers=sorted(set(blockers)),
        warnings=["M067R gate allows one source-bundle bootstrap vertical slice only"],
    )


def build_lambda_remote_dependency_bundle_gate_check_from_paths(
    *,
    plan: str | Path,
) -> LambdaRemoteVerticalSliceGateCheck:
    plan_report = load_lambda_remote_vertical_slice_execution_plan(plan)
    blockers = list(plan_report.blockers)
    if plan_report.milestone not in {
        M068R_MILESTONE,
        M071R_MILESTONE,
        M073R_MILESTONE,
        M075R_MILESTONE,
        M077R_MILESTONE,
        M079R_MILESTONE,
        M081R_MILESTONE,
        M083R_MILESTONE,
        M085R_MILESTONE,
        M087R_MILESTONE,
        M089R_MILESTONE,
        M093R_MILESTONE,
    }:
        blockers.append("dependency_bundle_plan_required")
    if plan_report.plan_status != "plan_passed":
        blockers.append(f"{plan_report.milestone.lower()}_plan_not_passed")
    if not plan_report.source_bundle_sha256:
        blockers.append("source_bundle_sha256_required")
    if not plan_report.dependency_bundle_sha256:
        blockers.append("dependency_bundle_sha256_required")
    if plan_report.max_uploaded_bundles != 2:
        blockers.append("exactly_two_bundle_uploads_required")
    if not plan_report.single_source_bundle_upload_allowed:
        blockers.append("single_source_bundle_upload_not_allowed")
    return LambdaRemoteVerticalSliceGateCheck(
        milestone=plan_report.milestone,
        gate_passed=not blockers,
        selected_candidate=plan_report.selected_candidate,
        selected_region=plan_report.selected_region,
        selected_ssh_key_hash=plan_report.selected_ssh_key_hash,
        command_manifest_hash=plan_report.command_manifest_hash,
        source_bundle_sha256=plan_report.source_bundle_sha256,
        dependency_bundle_sha256=plan_report.dependency_bundle_sha256,
        declared_artifact_policy_hash=plan_report.declared_artifact_policy_hash,
        max_uploaded_bundles=2,
        single_source_bundle_upload_allowed=True,
        max_remote_commands=plan_report.max_remote_command_attempts,
        response_capture_active=plan_report.response_capture_active,
        status_before_parse=plan_report.status_before_parse,
        effective_launch_timeout_seconds=plan_report.effective_launch_timeout_seconds,
        blockers=sorted(set(blockers)),
        warnings=[
            (
                "M089R gate allows one complete bounded synthetic DiLoCo "
                "experiment command after bounded setup"
                if plan_report.milestone == M089R_MILESTONE
                else (
                "M087R gate allows one bounded parameter-fragment smoke command "
                "after bounded setup"
                )
                if plan_report.milestone == M087R_MILESTONE
                else (
                "M083R gate allows one bounded optimizer-fidelity smoke command "
                "after bounded setup"
                )
                if plan_report.milestone == M083R_MILESTONE
                else (
                    "M085R gate allows one bounded integrated DiLoCo smoke command "
                    "after bounded setup"
                )
                if plan_report.milestone == M085R_MILESTONE
                else (
                    "M081R gate allows one bounded DiLoCo-shaped synthetic command "
                    "after bounded setup"
                )
                if plan_report.milestone == M081R_MILESTONE
                else (
                    "M079R gate allows one bounded learner/syncer smoke command "
                    "after bounded setup"
                )
                if plan_report.milestone == M079R_MILESTONE
                else (
                    "M077R gate allows one bounded synthetic experiment command "
                    "after bounded setup"
                )
                if plan_report.milestone == M077R_MILESTONE
                else "M075R gate allows one runtime/protocol smoke command after bounded setup"
                if plan_report.milestone == M075R_MILESTONE
                else "M073R gate allows one tiny-smoke command after bounded setup"
                if plan_report.milestone == M073R_MILESTONE
                else "M071R gate allows one first-experiment command after bounded setup"
                if plan_report.milestone == M071R_MILESTONE
                else "M068R gate allows one source bundle and one local wheelhouse bundle only"
            )
        ],
    )


def build_lambda_remote_vertical_slice_one_shot_arming_from_paths(
    *,
    gate_check: str | Path,
    manifest: str | Path,
    response_loss_controls: str | Path,
    expires_minutes: int,
    created_at_utc: str | None = None,
) -> LambdaRemoteVerticalSliceOneShotArming:
    paths = {
        "gate_check": str(gate_check),
        "manifest": str(manifest),
        "response_loss_controls": str(response_loss_controls),
    }
    hashes = {
        name: _sha256_file(path)
        for name, path in paths.items()
        if Path(path).exists()
    }
    gate = load_lambda_remote_vertical_slice_gate_check(gate_check)
    manifest_report = load_lambda_remote_vertical_slice_command_manifest(manifest)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    blockers = list(gate.blockers)
    if not gate.gate_passed:
        blockers.append("m066r_gate_not_passed")
    if hashes.get("manifest") != gate.command_manifest_hash:
        blockers.append("m066r_manifest_hash_mismatch")
    if len(manifest_report.command_entries) != gate.max_remote_commands:
        blockers.append("m066r_manifest_command_count_mismatch")
    if not controls.controls_passed or not controls.no_auto_launch_retry:
        blockers.extend(controls.blockers or ["response_loss_controls_not_passed"])
    if expires_minutes <= 0:
        blockers.append("expiration_required")
    created = _parse_utc(created_at_utc) if created_at_utc else datetime.now(timezone.utc)
    expires = created + timedelta(minutes=expires_minutes)
    status: Literal["not_armed", "armed_for_one_shot_m066r_remote_vertical_slice"] = (
        "armed_for_one_shot_m066r_remote_vertical_slice" if not blockers else "not_armed"
    )
    arming_id = "m066r-remote-vslice-" + _hash_json(
        {
            "created_at_utc": _format_utc(created),
            "expires_at_utc": _format_utc(expires),
            "artifact_hashes": hashes,
            "selected_candidate": gate.selected_candidate,
            "selected_region": gate.selected_region,
        }
    )[:16]
    return LambdaRemoteVerticalSliceOneShotArming(
        arming_id=arming_id,
        arming_status=status,
        selected_candidate=gate.selected_candidate,
        selected_region=gate.selected_region,
        command_manifest_hash=gate.command_manifest_hash,
        max_remote_command_attempts=gate.max_remote_commands,
        created_at_utc=_format_utc(created),
        expires_at_utc=_format_utc(expires),
        artifact_hashes=hashes,
        artifact_paths=paths,
        blockers=sorted(set(blockers)),
        warnings=[
            "M066R arming is preview-only; reviewer bridge exposes one-shot permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def build_lambda_remote_source_bundle_one_shot_arming_from_paths(
    *,
    gate_check: str | Path,
    command_manifest: str | Path,
    source_bundle_validation: str | Path,
    response_loss_controls: str | Path,
    expires_minutes: int,
    created_at_utc: str | None = None,
) -> LambdaRemoteVerticalSliceOneShotArming:
    paths = {
        "gate_check": str(gate_check),
        "command_manifest": str(command_manifest),
        "source_bundle_validation": str(source_bundle_validation),
        "response_loss_controls": str(response_loss_controls),
    }
    hashes = {name: _sha256_file(path) for name, path in paths.items() if Path(path).exists()}
    gate = load_lambda_remote_vertical_slice_gate_check(gate_check)
    manifest = load_lambda_remote_vertical_slice_command_manifest(command_manifest)
    bundle_validation = load_lambda_remote_source_bundle_validation(
        source_bundle_validation
    )
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    blockers = list(gate.blockers)
    if gate.milestone != M067R_MILESTONE:
        blockers.append("m067r_gate_required")
    if not gate.gate_passed:
        blockers.append("m067r_gate_not_passed")
    if manifest.milestone != M067R_MILESTONE:
        blockers.append("m067r_manifest_required")
    if len(manifest.command_entries) != gate.max_remote_commands:
        blockers.append("m067r_manifest_command_count_mismatch")
    if not bundle_validation.validation_passed:
        blockers.extend(bundle_validation.blockers or ["source_bundle_validation_failed"])
    if bundle_validation.bundle_sha256 != gate.source_bundle_sha256:
        blockers.append("source_bundle_hash_mismatch")
    if not controls.controls_passed or not controls.no_auto_launch_retry:
        blockers.extend(controls.blockers or ["response_loss_controls_not_passed"])
    if expires_minutes <= 0:
        blockers.append("expiration_required")
    created = _parse_utc(created_at_utc) if created_at_utc else datetime.now(timezone.utc)
    expires = created + timedelta(minutes=expires_minutes)
    status: Literal[
        "not_armed",
        "armed_for_one_shot_m066r_remote_vertical_slice",
        "armed_for_one_shot_m067r_source_bundle_vertical_slice",
    ] = "armed_for_one_shot_m067r_source_bundle_vertical_slice" if not blockers else "not_armed"
    arming_id = "m067r-source-bundle-" + _hash_json(
        {
            "created_at_utc": _format_utc(created),
            "expires_at_utc": _format_utc(expires),
            "artifact_hashes": hashes,
            "source_bundle_sha256": bundle_validation.bundle_sha256,
            "selected_candidate": gate.selected_candidate,
            "selected_region": gate.selected_region,
        }
    )[:16]
    return LambdaRemoteVerticalSliceOneShotArming(
        arming_id=arming_id,
        arming_status=status,
        armed_for=M067R_ARMED_FOR,
        selected_candidate=gate.selected_candidate,
        selected_region=gate.selected_region,
        command_manifest_hash=gate.command_manifest_hash,
        source_bundle_sha256=bundle_validation.bundle_sha256,
        max_remote_command_attempts=gate.max_remote_commands,
        max_uploaded_bundles=1,
        single_source_bundle_upload_allowed=True,
        created_at_utc=_format_utc(created),
        expires_at_utc=_format_utc(expires),
        artifact_hashes=hashes,
        artifact_paths=paths,
        blockers=sorted(set(blockers)),
        warnings=[
            "M067R arming binds the source bundle hash and command manifest hash",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def build_lambda_remote_dependency_bundle_one_shot_arming_from_paths(
    *,
    gate_check: str | Path,
    plan: str | Path | None = None,
    command_manifest: str | Path,
    source_bundle_validation: str | Path,
    dependency_bundle_validation: str | Path,
    response_loss_controls: str | Path,
    expires_minutes: int,
    failure_artifact_capture_policy: str | Path | None = None,
    artifact_body_policy: str | Path | None = None,
    declared_artifact_policy: str | Path | None = None,
    created_at_utc: str | None = None,
) -> LambdaRemoteVerticalSliceOneShotArming:
    from decodilo.lambda_cloud.remote_dependency_bundle import (
        load_lambda_dependency_bundle_validation,
    )

    paths = {
        "gate_check": str(gate_check),
        "command_manifest": str(command_manifest),
        "source_bundle_validation": str(source_bundle_validation),
        "dependency_bundle_validation": str(dependency_bundle_validation),
        "response_loss_controls": str(response_loss_controls),
    }
    if plan is not None:
        paths["plan"] = str(plan)
    if failure_artifact_capture_policy is not None:
        paths["failure_artifact_capture_policy"] = str(
            failure_artifact_capture_policy
        )
    if artifact_body_policy is not None:
        paths["artifact_body_policy"] = str(artifact_body_policy)
    if declared_artifact_policy is not None:
        paths["declared_artifact_policy"] = str(declared_artifact_policy)
    hashes = {name: _sha256_file(path) for name, path in paths.items() if Path(path).exists()}
    gate = load_lambda_remote_vertical_slice_gate_check(gate_check)
    manifest = load_lambda_remote_vertical_slice_command_manifest(command_manifest)
    source_validation = load_lambda_remote_source_bundle_validation(
        source_bundle_validation
    )
    dependency_validation = load_lambda_dependency_bundle_validation(
        dependency_bundle_validation
    )
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    blockers = list(gate.blockers)
    if gate.milestone not in {
        M068R_MILESTONE,
        M071R_MILESTONE,
        M073R_MILESTONE,
        M075R_MILESTONE,
        M077R_MILESTONE,
        M079R_MILESTONE,
        M081R_MILESTONE,
        M083R_MILESTONE,
        M085R_MILESTONE,
        M087R_MILESTONE,
        M089R_MILESTONE,
        M093R_MILESTONE,
    }:
        blockers.append("dependency_bundle_gate_required")
    if not gate.gate_passed:
        blockers.append(f"{gate.milestone.lower()}_gate_not_passed")
    if manifest.milestone != gate.milestone:
        blockers.append("dependency_bundle_manifest_gate_milestone_mismatch")
    if (
        manifest.milestone == M071R_MILESTONE
        and not _m071r_manifest_contains_exact_experiment_command(manifest)
    ):
        blockers.append("m071r_exact_first_experiment_command_required")
    if (
        manifest.milestone == M073R_MILESTONE
        and not _m073r_manifest_contains_exact_tiny_smoke_command(manifest)
    ):
        blockers.append("m073r_exact_tiny_smoke_command_required")
    if (
        manifest.milestone == M075R_MILESTONE
        and not _m075r_manifest_contains_exact_runtime_smoke_command(manifest)
    ):
        blockers.append("m075r_exact_runtime_smoke_command_required")
    if (
        manifest.milestone == M077R_MILESTONE
        and not _m077r_manifest_contains_exact_synthetic_experiment_command(manifest)
    ):
        blockers.append("m077r_exact_synthetic_experiment_command_required")
    if (
        manifest.milestone == M079R_MILESTONE
        and not _m079r_manifest_contains_exact_learner_syncer_smoke_command(manifest)
    ):
        blockers.append("m079r_exact_learner_syncer_smoke_command_required")
    if (
        manifest.milestone == M081R_MILESTONE
        and not _m081r_manifest_contains_exact_diloco_smoke_command(manifest)
    ):
        blockers.append("m081r_exact_diloco_smoke_command_required")
    if (
        manifest.milestone == M083R_MILESTONE
        and not _m083r_manifest_contains_exact_diloco_optimizer_smoke_command(manifest)
    ):
        blockers.append("m083r_exact_diloco_optimizer_smoke_command_required")
    if (
        manifest.milestone == M085R_MILESTONE
        and not _m085r_manifest_contains_exact_integrated_diloco_smoke_command(manifest)
    ):
        blockers.append("m085r_exact_integrated_diloco_smoke_command_required")
    if (
        manifest.milestone == M087R_MILESTONE
        and not _m087r_manifest_contains_exact_parameter_fragment_smoke_command(manifest)
    ):
        blockers.append("m087r_exact_parameter_fragment_smoke_command_required")
    if (
        manifest.milestone == M089R_MILESTONE
        and not _m089r_manifest_contains_exact_bounded_diloco_experiment_command(
            manifest
        )
    ):
        blockers.append("m089r_exact_bounded_diloco_experiment_command_required")
    if (
        manifest.milestone == M093R_MILESTONE
        and not _m093r_manifest_contains_exact_tiny_real_training_smoke_command(
            manifest
        )
    ):
        blockers.append("m093r_exact_tiny_real_training_smoke_command_required")
    if len(manifest.command_entries) != gate.max_remote_commands:
        blockers.append("m068r_manifest_command_count_mismatch")
    if not source_validation.validation_passed:
        blockers.extend(source_validation.blockers or ["source_bundle_validation_failed"])
    if not dependency_validation.validation_passed:
        blockers.extend(
            dependency_validation.blockers or ["dependency_bundle_validation_failed"]
        )
    if source_validation.bundle_sha256 != gate.source_bundle_sha256:
        blockers.append("source_bundle_hash_mismatch")
    if dependency_validation.bundle_sha256 != gate.dependency_bundle_sha256:
        blockers.append("dependency_bundle_hash_mismatch")
    if not controls.controls_passed or not controls.no_auto_launch_retry:
        blockers.extend(controls.blockers or ["response_loss_controls_not_passed"])
    if gate.milestone == M075R_MILESTONE and failure_artifact_capture_policy is not None:
        from decodilo.lambda_cloud.remote_vslice_failure_artifact_capture_policy import (
            load_lambda_remote_vslice_failure_artifact_capture_policy,
        )

        capture_policy = load_lambda_remote_vslice_failure_artifact_capture_policy(
            failure_artifact_capture_policy
        )
        if not capture_policy.policy_passed:
            blockers.extend(
                capture_policy.blockers
                or ["failure_artifact_capture_policy_not_passed"]
            )
        if not capture_policy.capture_on_failure_allowed:
            blockers.append("failure_artifact_capture_not_allowed")
        if capture_policy.capture_scope != "predeclared_artifact_only":
            blockers.append("failure_artifact_capture_scope_not_predeclared_only")
        if capture_policy.expected_output_artifact_path != M075R_OUTPUT_ARTIFACT_PATH:
            blockers.append("failure_artifact_capture_path_mismatch")
        if not capture_policy.no_arbitrary_file_read:
            blockers.append("failure_artifact_policy_allows_arbitrary_file_read")
    if gate.milestone == M075R_MILESTONE and artifact_body_policy is not None:
        from decodilo.lambda_cloud.runtime_smoke_artifact_body_policy import (
            load_lambda_runtime_smoke_artifact_body_policy,
        )

        body_policy = load_lambda_runtime_smoke_artifact_body_policy(
            artifact_body_policy
        )
        if body_policy.policy_status != "policy_defined":
            blockers.extend(body_policy.blockers or ["artifact_body_policy_not_defined"])
        if not body_policy.content_capture_allowed:
            blockers.append("artifact_body_capture_not_allowed")
        if body_policy.declared_artifact_path != M075R_OUTPUT_ARTIFACT_PATH:
            blockers.append("artifact_body_policy_path_mismatch")
        if not body_policy.no_arbitrary_file_reads:
            blockers.append("artifact_body_policy_allows_arbitrary_file_read")
        if not body_policy.no_directory_reads:
            blockers.append("artifact_body_policy_allows_directory_read")
    if (
        gate.milestone
        in {
            M079R_MILESTONE,
            M081R_MILESTONE,
            M083R_MILESTONE,
            M085R_MILESTONE,
            M087R_MILESTONE,
            M089R_MILESTONE,
            M093R_MILESTONE,
        }
        and declared_artifact_policy is not None
    ):
        policy_payload = json.loads(
            Path(declared_artifact_policy).read_text(encoding="utf-8")
        )
        if policy_payload.get("policy_status") == "manifest_artifact_policy_defined":
            from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
                load_lambda_remote_vslice_manifest_artifact_policy,
            )

            manifest_policy = load_lambda_remote_vslice_manifest_artifact_policy(
                declared_artifact_policy
            )
            if manifest_policy.policy_status != "manifest_artifact_policy_defined":
                blockers.extend(
                    manifest_policy.blockers
                    or ["manifest_artifact_policy_not_defined"]
                )
            if (
                manifest_policy.declared_artifact_path
                != _output_artifact_path_for_milestone(gate.milestone)
            ):
                blockers.append("declared_artifact_policy_path_mismatch")
            if not manifest_policy.accept_only_manifest_declared_paths:
                blockers.append("declared_artifact_policy_not_manifest_driven")
            if not manifest_policy.capture_on_success:
                blockers.append("declared_artifact_policy_disallows_success_capture")
            if not manifest_policy.capture_on_failure:
                blockers.append("declared_artifact_policy_disallows_failure_capture")
            if not manifest_policy.no_arbitrary_file_reads:
                blockers.append("declared_artifact_policy_allows_arbitrary_file_read")
            if not manifest_policy.reject_directories:
                blockers.append("declared_artifact_policy_allows_directory_read")
            if not manifest_policy.reject_globs:
                blockers.append("declared_artifact_policy_allows_globs")
            if not manifest_policy.reject_fallback_paths:
                blockers.append("declared_artifact_policy_allows_fallback_paths")
            if not manifest_policy.reject_relative_paths:
                blockers.append("declared_artifact_policy_allows_relative_paths")
            if not manifest_policy.reject_traversal:
                blockers.append("declared_artifact_policy_allows_traversal")
            if not manifest_policy.reject_symlink_escapes:
                blockers.append("declared_artifact_policy_allows_symlink_escape")
            if (
                gate.milestone == M079R_MILESTONE
                and not manifest_policy.learner_syncer_declared_artifact_supported
            ):
                blockers.append("manifest_artifact_policy_learner_syncer_path_missing")
            if (
                gate.milestone == M081R_MILESTONE
                and not manifest_policy.diloco_smoke_declared_artifact_supported
            ):
                blockers.append("manifest_artifact_policy_diloco_path_missing")
            if (
                gate.milestone == M083R_MILESTONE
                and not manifest_policy.diloco_optimizer_smoke_declared_artifact_supported
            ):
                blockers.append("manifest_artifact_policy_diloco_optimizer_path_missing")
            if (
                gate.milestone == M085R_MILESTONE
                and not manifest_policy.integrated_diloco_smoke_declared_artifact_supported
            ):
                blockers.append("manifest_artifact_policy_integrated_diloco_path_missing")
            if (
                gate.milestone == M087R_MILESTONE
                and not manifest_policy.parameter_fragment_smoke_declared_artifact_supported
            ):
                blockers.append("manifest_artifact_policy_parameter_fragment_path_missing")
            if (
                gate.milestone == M089R_MILESTONE
                and not manifest_policy.bounded_diloco_experiment_declared_artifact_supported
            ):
                blockers.append("manifest_artifact_policy_bounded_diloco_path_missing")
            if (
                gate.milestone == M093R_MILESTONE
                and not manifest_policy.tiny_real_training_smoke_declared_artifact_supported
            ):
                blockers.append("manifest_artifact_policy_tiny_real_training_path_missing")
        else:
            from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
                load_lambda_remote_vslice_declared_artifact_policy,
            )

            declared_policy = load_lambda_remote_vslice_declared_artifact_policy(
                declared_artifact_policy
            )
            if declared_policy.policy_status != "policy_defined":
                blockers.extend(
                    declared_policy.blockers or ["declared_artifact_policy_not_defined"]
                )
            if (
                declared_policy.declared_artifact_path
                != _output_artifact_path_for_milestone(gate.milestone)
            ):
                blockers.append("declared_artifact_policy_path_mismatch")
            if not declared_policy.no_arbitrary_file_reads:
                blockers.append("declared_artifact_policy_allows_arbitrary_file_read")
            if not declared_policy.reject_directories:
                blockers.append("declared_artifact_policy_allows_directory_read")
            if not declared_policy.reject_globs:
                blockers.append("declared_artifact_policy_allows_globs")
            if not declared_policy.reject_fallback_paths:
                blockers.append("declared_artifact_policy_allows_fallback_paths")
        if hashes.get("declared_artifact_policy") != gate.declared_artifact_policy_hash:
            blockers.append("declared_artifact_policy_hash_mismatch")
    if expires_minutes <= 0:
        blockers.append("expiration_required")
    created = _parse_utc(created_at_utc) if created_at_utc else datetime.now(timezone.utc)
    expires = created + timedelta(minutes=expires_minutes)
    status: Literal[
        "not_armed",
        "armed_for_one_shot_m066r_remote_vertical_slice",
        "armed_for_one_shot_m067r_source_bundle_vertical_slice",
        "armed_for_one_shot_m068r_dependency_bundle_vertical_slice",
        "armed_for_one_shot_m071r_first_experiment",
        "armed_for_one_shot_m073r_tiny_smoke",
        "armed_for_one_shot_m075r_runtime_protocol_smoke",
        "armed_for_one_shot_m077r_first_synthetic_experiment",
        "armed_for_one_shot_m079r_next_synthetic_experiment",
        "armed_for_one_shot_m081r_diloco_synthetic_experiment",
        "armed_for_one_shot_m083r_diloco_optimizer_smoke",
        "armed_for_one_shot_m085r_integrated_diloco_smoke",
        "armed_for_one_shot_m087r_parameter_fragment_smoke",
        "armed_for_one_shot_m089r_bounded_diloco_experiment",
        "armed_for_one_shot_m093r_tiny_real_training_smoke",
    ] = (
        "armed_for_one_shot_m093r_tiny_real_training_smoke"
        if gate.milestone == M093R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m089r_bounded_diloco_experiment"
        if gate.milestone == M089R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m087r_parameter_fragment_smoke"
        if gate.milestone == M087R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m085r_integrated_diloco_smoke"
        if gate.milestone == M085R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m083r_diloco_optimizer_smoke"
        if gate.milestone == M083R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m081r_diloco_synthetic_experiment"
        if gate.milestone == M081R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m079r_next_synthetic_experiment"
        if gate.milestone == M079R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m077r_first_synthetic_experiment"
        if gate.milestone == M077R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m075r_runtime_protocol_smoke"
        if gate.milestone == M075R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m073r_tiny_smoke"
        if gate.milestone == M073R_MILESTONE and not blockers
        else
        "armed_for_one_shot_m071r_first_experiment"
        if gate.milestone == M071R_MILESTONE and not blockers
        else "armed_for_one_shot_m068r_dependency_bundle_vertical_slice"
        if not blockers
        else "not_armed"
    )
    arming_id_prefix = (
        "m093r-tiny-real-training-smoke-"
        if gate.milestone == M093R_MILESTONE
        else
        "m089r-bounded-diloco-experiment-"
        if gate.milestone == M089R_MILESTONE
        else
        "m087r-parameter-fragment-smoke-"
        if gate.milestone == M087R_MILESTONE
        else
        "m085r-integrated-diloco-smoke-"
        if gate.milestone == M085R_MILESTONE
        else
        "m083r-diloco-optimizer-smoke-"
        if gate.milestone == M083R_MILESTONE
        else
        "m081r-diloco-synthetic-experiment-"
        if gate.milestone == M081R_MILESTONE
        else
        "m079r-next-synthetic-experiment-"
        if gate.milestone == M079R_MILESTONE
        else
        "m077r-first-synthetic-experiment-"
        if gate.milestone == M077R_MILESTONE
        else
        "m075r-runtime-protocol-smoke-"
        if gate.milestone == M075R_MILESTONE
        else
        "m073r-tiny-smoke-"
        if gate.milestone == M073R_MILESTONE
        else
        "m071r-first-experiment-"
        if gate.milestone == M071R_MILESTONE
        else "m068r-dependency-bundle-"
    )
    arming_id = arming_id_prefix + _hash_json(
        {
            "created_at_utc": _format_utc(created),
            "expires_at_utc": _format_utc(expires),
            "artifact_hashes": hashes,
            "source_bundle_sha256": source_validation.bundle_sha256,
            "dependency_bundle_sha256": dependency_validation.bundle_sha256,
            "selected_candidate": gate.selected_candidate,
            "selected_region": gate.selected_region,
        }
    )[:16]
    arming_warning_by_milestone = {
        M093R_MILESTONE: (
            "M093R arming binds source, dependency, and tiny real-training "
            "smoke manifest hashes"
        ),
        M089R_MILESTONE: (
            "M089R arming binds source, dependency, and bounded DiLoCo "
            "experiment manifest hashes"
        ),
        M087R_MILESTONE: (
            "M087R arming binds source, dependency, and parameter-fragment "
            "smoke manifest hashes"
        ),
        M085R_MILESTONE: (
            "M085R arming binds source, dependency, and integrated DiLoCo "
            "smoke manifest hashes"
        ),
        M083R_MILESTONE: (
            "M083R arming binds source, dependency, and optimizer-fidelity "
            "smoke manifest hashes"
        ),
        M081R_MILESTONE: (
            "M081R arming binds source, dependency, and DiLoCo-shaped "
            "smoke manifest hashes"
        ),
        M079R_MILESTONE: (
            "M079R arming binds source, dependency, and learner/syncer "
            "smoke manifest hashes"
        ),
        M077R_MILESTONE: (
            "M077R arming binds source, dependency, and synthetic experiment "
            "manifest hashes"
        ),
        M075R_MILESTONE: (
            "M075R arming binds source, dependency, and runtime/protocol "
            "smoke manifest hashes"
        ),
        M073R_MILESTONE: (
            "M073R arming binds source, dependency, and tiny-smoke manifest hashes"
        ),
        M071R_MILESTONE: (
            "M071R arming binds source, dependency, and first-experiment manifest hashes"
        ),
    }
    return LambdaRemoteVerticalSliceOneShotArming(
        arming_id=arming_id,
        arming_status=status,
        armed_for=(
            M093R_ARMED_FOR
            if gate.milestone == M093R_MILESTONE
            else
            M089R_ARMED_FOR
            if gate.milestone == M089R_MILESTONE
            else
            M087R_ARMED_FOR
            if gate.milestone == M087R_MILESTONE
            else
            M085R_ARMED_FOR
            if gate.milestone == M085R_MILESTONE
            else
            M083R_ARMED_FOR
            if gate.milestone == M083R_MILESTONE
            else
            M081R_ARMED_FOR
            if gate.milestone == M081R_MILESTONE
            else
            M079R_ARMED_FOR
            if gate.milestone == M079R_MILESTONE
            else
            M077R_ARMED_FOR
            if gate.milestone == M077R_MILESTONE
            else
            M075R_ARMED_FOR
            if gate.milestone == M075R_MILESTONE
            else
            M073R_ARMED_FOR
            if gate.milestone == M073R_MILESTONE
            else
            M071R_ARMED_FOR
            if gate.milestone == M071R_MILESTONE
            else M068R_ARMED_FOR
        ),
        selected_candidate=gate.selected_candidate,
        selected_region=gate.selected_region,
        command_manifest_hash=gate.command_manifest_hash,
        source_bundle_sha256=source_validation.bundle_sha256,
        dependency_bundle_sha256=dependency_validation.bundle_sha256,
        failure_artifact_capture_policy_hash=hashes.get(
            "failure_artifact_capture_policy"
        ),
        artifact_body_policy_hash=hashes.get("artifact_body_policy"),
        declared_artifact_policy_hash=hashes.get("declared_artifact_policy"),
        max_remote_command_attempts=gate.max_remote_commands,
        max_uploaded_bundles=2,
        single_source_bundle_upload_allowed=True,
        created_at_utc=_format_utc(created),
        expires_at_utc=_format_utc(expires),
        artifact_hashes=hashes,
        artifact_paths=paths,
        blockers=sorted(set(blockers)),
        warnings=[
            arming_warning_by_milestone.get(
                gate.milestone,
                "M068R arming binds source and dependency bundle hashes",
            ),
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def build_lambda_remote_vertical_slice_reviewer_bridge_from_path(
    *,
    arming: str | Path,
    now_utc: str | None = None,
) -> LambdaRemoteVerticalSliceReviewerBridge:
    arming_report = load_lambda_remote_vertical_slice_one_shot_arming(arming)
    blockers = list(arming_report.blockers)
    if arming_report.armed_for == M093R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m093r_tiny_real_training_smoke"
    elif arming_report.armed_for == M089R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m089r_bounded_diloco_experiment"
    elif arming_report.armed_for == M087R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m087r_parameter_fragment_smoke"
    elif arming_report.armed_for == M085R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m085r_integrated_diloco_smoke"
    elif arming_report.armed_for == M083R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m083r_diloco_optimizer_smoke"
    elif arming_report.armed_for == M081R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m081r_diloco_synthetic_experiment"
    elif arming_report.armed_for == M079R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m079r_next_synthetic_experiment"
    elif arming_report.armed_for == M077R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m077r_first_synthetic_experiment"
    elif arming_report.armed_for == M075R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m075r_runtime_protocol_smoke"
    elif arming_report.armed_for == M073R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m073r_tiny_smoke"
    elif arming_report.armed_for == M071R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m071r_first_experiment"
    elif arming_report.armed_for == M068R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m068r_dependency_bundle_vertical_slice"
    elif arming_report.armed_for == M067R_ARMED_FOR:
        expected_status = "armed_for_one_shot_m067r_source_bundle_vertical_slice"
    else:
        expected_status = "armed_for_one_shot_m066r_remote_vertical_slice"
    if arming_report.arming_status != expected_status:
        blockers.append("m066r_one_shot_arming_not_armed")
    if is_lambda_remote_vertical_slice_one_shot_arming_expired(
        arming_report,
        now_utc=now_utc,
    ):
        blockers.append("m066r_one_shot_arming_expired")
    status: Literal["not_ready", "reviewer_compatible_one_shot_ready"] = (
        "reviewer_compatible_one_shot_ready" if not blockers else "not_ready"
    )
    return LambdaRemoteVerticalSliceReviewerBridge(
        bridge_status=status,
        one_shot_request_send_permitted=status == "reviewer_compatible_one_shot_ready",
        one_shot_ssh_connectivity_probe_permitted=(
            status == "reviewer_compatible_one_shot_ready"
        ),
        one_shot_remote_vertical_slice_permitted=(
            status == "reviewer_compatible_one_shot_ready"
        ),
        one_shot_minimal_remote_command_permitted=(
            status == "reviewer_compatible_one_shot_ready"
        ),
        selected_candidate=arming_report.selected_candidate,
        selected_region=arming_report.selected_region,
        command_manifest_hash=arming_report.command_manifest_hash,
        source_bundle_sha256=arming_report.source_bundle_sha256,
        dependency_bundle_sha256=arming_report.dependency_bundle_sha256,
        failure_artifact_capture_policy_hash=(
            arming_report.failure_artifact_capture_policy_hash
        ),
        artifact_body_policy_hash=arming_report.artifact_body_policy_hash,
        declared_artifact_policy_hash=arming_report.declared_artifact_policy_hash,
        max_remote_command_attempts=arming_report.max_remote_command_attempts,
        max_uploaded_bundles=arming_report.max_uploaded_bundles,
        single_source_bundle_upload_allowed=(
            arming_report.single_source_bundle_upload_allowed
        ),
        expires_at_utc=arming_report.expires_at_utc,
        blockers=sorted(set(blockers)),
        warnings=[
            "M066R bridge is the only artifact exposing one-shot request-send permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def is_lambda_remote_vertical_slice_one_shot_arming_expired(
    report: LambdaRemoteVerticalSliceOneShotArming,
    *,
    now_utc: str | None = None,
) -> bool:
    now = _parse_utc(now_utc) if now_utc else datetime.now(timezone.utc)
    return now >= _parse_utc(report.expires_at_utc)


def run_lambda_remote_vertical_slice_manifest(
    *,
    owned_instance_id: str,
    instance_payload: dict[str, Any],
    private_key_path: Path | None,
    manifest: LambdaRemoteVerticalSliceCommandManifest,
    manifest_hash: str,
    source_bundle_path: Path | None = None,
    source_bundle_sha256: str | None = None,
    dependency_bundle_path: Path | None = None,
    dependency_bundle_sha256: str | None = None,
    ssh_username: str = "ubuntu",
    ssh_port_ready_timeout_seconds: float = 300.0,
    ssh_port_poll_interval_seconds: float = 5.0,
    ssh_port_connect_timeout_seconds: float = 3.0,
    ssh_banner_ready_timeout_seconds: float = 120.0,
    ssh_banner_poll_interval_seconds: float = 2.0,
    ssh_banner_read_timeout_seconds: float = 5.0,
    fake_mode: bool = False,
    host_discovery_result: LambdaSSHHostDiscoveryResult | None = None,
) -> LambdaRemoteVerticalSliceEvidence:
    from decodilo.lambda_cloud.ssh_host_discovery import (
        extract_ssh_host_from_instance_metadata,
    )

    if host_discovery_result is None:
        host_discovery_result = extract_ssh_host_from_instance_metadata(instance_payload)
    remote_source_bundle_path = _remote_source_bundle_path_for_milestone(
        manifest.milestone
    )
    output_artifact_path = _output_artifact_path_for_milestone(manifest.milestone)
    approved_command = (
        M093R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M093R_MILESTONE
        else
        M089R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M089R_MILESTONE
        else
        M087R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M087R_MILESTONE
        else
        M085R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M085R_MILESTONE
        else
        M083R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M083R_MILESTONE
        else
        M081R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M081R_MILESTONE
        else
        M079R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M079R_MILESTONE
        else
        M077R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M077R_MILESTONE
        else
        M075R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M075R_MILESTONE
        else
        M073R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M073R_MILESTONE
        else
        M071R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M071R_MILESTONE
        else
        M068R_MANIFEST_COMMAND_LABEL
        if manifest.milestone == M068R_MILESTONE
        else M067R_MANIFEST_COMMAND_LABEL
        if source_bundle_path is not None
        else M066R_MANIFEST_COMMAND_LABEL
    )
    base_fields = {
        "milestone": manifest.milestone,
        "owned_instance_id_redacted": redact_instance_id(owned_instance_id),
        "host_discovery_attempted": True,
        "host_discovery_status": host_discovery_result.status,
        "host_discovery_source_path": host_discovery_result.source_path,
        "host_discovery_poll_count": host_discovery_result.poll_count,
        "host_discovery_duration_seconds": host_discovery_result.duration_seconds,
        "sanitized_metadata_keys": host_discovery_result.sanitized_metadata_keys,
        "sanitized_metadata_key_paths": host_discovery_result.sanitized_metadata_key_paths,
        "command_manifest_hash": manifest_hash,
        "command_count": len(manifest.command_entries),
        "ssh_username": ssh_username,
        "approved_command": approved_command,
        "source_bundle_sha256": source_bundle_sha256,
        "source_bundle_remote_path": (
            remote_source_bundle_path if source_bundle_path is not None else None
        ),
        "dependency_bundle_sha256": dependency_bundle_sha256,
        "dependency_bundle_remote_path": (
            M068R_REMOTE_DEPENDENCY_BUNDLE_PATH
            if dependency_bundle_path is not None
            else None
        ),
    }
    if host_discovery_result.status != "FOUND" or not host_discovery_result.host:
        return LambdaRemoteVerticalSliceEvidence(
            **base_fields,
            auth_result="host_discovery_failed",
            vertical_slice_status="host_discovery_failed",
            blockers=["ssh_host_not_present_in_provider_metadata"],
        )
    if fake_mode:
        stage_results = [
            LambdaRemoteVerticalSliceStageResult(
                stage=entry.stage,
                command_hash=_hash_json(entry.model_dump(mode="json"))[:16],
                exact_command_redacted="<redacted-m066r-command>",
                exit_code=0,
                stdout_redacted=f"<redacted-{entry.stage}-stdout>",
                stdout_sha256_prefix=_hash_text(f"fake-{entry.exact_command}\n")[:16],
                elapsed_seconds=0.0,
                passed=True,
            )
            for entry in manifest.command_entries
        ]
        return LambdaRemoteVerticalSliceEvidence(
            **base_fields,
            probe_attempted=True,
            probe_completed=True,
            probe_passed=True,
            auth_result="remote_vertical_slice_succeeded",
            target_host_redacted=host_discovery_result.host_redacted or "<redacted-host>",
            ssh_key_present=private_key_path is not None,
            ssh_port_readiness_attempted=True,
            ssh_port_reachable=True,
            remote_command_attempted=True,
            remote_command_result="succeeded",
            source_bundle_upload_attempted=source_bundle_path is not None,
            source_bundle_upload_succeeded=source_bundle_path is not None,
            source_bundle_hash_verified=source_bundle_path is not None,
            dependency_bundle_upload_attempted=dependency_bundle_path is not None,
            dependency_bundle_upload_succeeded=dependency_bundle_path is not None,
            dependency_bundle_hash_verified=dependency_bundle_path is not None,
            uploaded_bundles_count=int(source_bundle_path is not None)
            + int(dependency_bundle_path is not None),
            local_dependency_install_attempted=_is_dependency_bundle_milestone(
                manifest.milestone
            ),
            local_dependency_install_succeeded=_is_dependency_bundle_milestone(
                manifest.milestone
            ),
            experiment_output_artifact_capture_attempted=(
                output_artifact_path is not None
            ),
            experiment_output_artifact_capture_succeeded=(
                output_artifact_path is not None
            ),
            experiment_output_artifact_path=output_artifact_path,
            experiment_output_artifact_exists=output_artifact_path is not None,
            experiment_output_artifact_bytes=128 if output_artifact_path else None,
            experiment_output_artifact_sha256=_hash_text(
                f"fake-{manifest.milestone.lower()}-artifact\n"
            )
            if output_artifact_path
            else None,
            experiment_output_artifact_secret_scan_passed=(
                True if output_artifact_path else None
            ),
            experiment_output_artifact_body_capture_attempted=(
                output_artifact_path
                in {
                    M075R_OUTPUT_ARTIFACT_PATH,
                    M077R_OUTPUT_ARTIFACT_PATH,
                    M079R_OUTPUT_ARTIFACT_PATH,
                    M081R_OUTPUT_ARTIFACT_PATH,
                    M083R_OUTPUT_ARTIFACT_PATH,
                    M085R_OUTPUT_ARTIFACT_PATH,
                    M087R_OUTPUT_ARTIFACT_PATH,
                    M089R_OUTPUT_ARTIFACT_PATH,
                    M093R_OUTPUT_ARTIFACT_PATH,
                }
            ),
            experiment_output_artifact_body_capture_succeeded=(
                output_artifact_path
                in {
                    M075R_OUTPUT_ARTIFACT_PATH,
                    M077R_OUTPUT_ARTIFACT_PATH,
                    M079R_OUTPUT_ARTIFACT_PATH,
                    M081R_OUTPUT_ARTIFACT_PATH,
                    M083R_OUTPUT_ARTIFACT_PATH,
                    M085R_OUTPUT_ARTIFACT_PATH,
                    M087R_OUTPUT_ARTIFACT_PATH,
                    M089R_OUTPUT_ARTIFACT_PATH,
                    M093R_OUTPUT_ARTIFACT_PATH,
                }
            ),
            experiment_output_artifact_body_persisted=(
                output_artifact_path
                in {
                    M075R_OUTPUT_ARTIFACT_PATH,
                    M077R_OUTPUT_ARTIFACT_PATH,
                    M079R_OUTPUT_ARTIFACT_PATH,
                    M081R_OUTPUT_ARTIFACT_PATH,
                    M083R_OUTPUT_ARTIFACT_PATH,
                    M085R_OUTPUT_ARTIFACT_PATH,
                    M087R_OUTPUT_ARTIFACT_PATH,
                    M089R_OUTPUT_ARTIFACT_PATH,
                    M093R_OUTPUT_ARTIFACT_PATH,
                }
            ),
            experiment_output_artifact_body_json=(
                {"runtime_smoke_status": "passed"}
                if output_artifact_path == M075R_OUTPUT_ARTIFACT_PATH
                else {"synthetic_experiment_status": "passed"}
                if output_artifact_path == M077R_OUTPUT_ARTIFACT_PATH
                else {"learner_syncer_smoke_status": "passed"}
                if output_artifact_path == M079R_OUTPUT_ARTIFACT_PATH
                else {
                    "diloco_smoke_status": "passed",
                    "optimization_fidelity": "diloco_shaped_protocol_only",
                    "inner_optimizer_semantics": "synthetic_placeholder",
                    "outer_optimizer_semantics": "token_weighted_merge",
                    "parameter_fragment_semantics": "not_exercised",
                }
                if output_artifact_path == M081R_OUTPUT_ARTIFACT_PATH
                else {
                    "diloco_optimizer_smoke_status": "passed",
                    "optimization_fidelity": "optimizer_semantics_smoke",
                    "inner_optimizer_semantics": "adamw",
                    "outer_optimizer_semantics": "nesterov",
                    "parameter_fragment_semantics": "not_exercised",
                }
                if output_artifact_path == M083R_OUTPUT_ARTIFACT_PATH
                else {
                    "integrated_diloco_smoke_status": "passed",
                    "optimization_fidelity": "integrated_optimizer_protocol_smoke",
                    "inner_optimizer_semantics": "adamw",
                    "outer_optimizer_semantics": "nesterov",
                    "parameter_fragment_semantics": "not_exercised",
                }
                if output_artifact_path == M085R_OUTPUT_ARTIFACT_PATH
                else {
                    "parameter_fragment_smoke_status": "passed",
                    "parameter_fragment_semantics": "synthetic_vector_fragments",
                    "fragment_count": 2,
                    "fragment_update_check_passed": True,
                    "fragment_merge_check_passed": True,
                    "fragment_reconstruction_check_passed": True,
                    "fragment_schedule_check_passed": True,
                    "fragment_state_roundtrip_check_passed": True,
                    "per_fragment_reference_check_passed": True,
                    "global_reference_check_passed": True,
                    "max_abs_error": 0.0,
                    "overlap_semantics": "not_exercised",
                    "quantization_semantics": "not_exercised",
                }
                if output_artifact_path == M087R_OUTPUT_ARTIFACT_PATH
                else {
                    "bounded_diloco_experiment_status": "passed",
                    "optimization_fidelity": "bounded_synthetic_diloco_experiment",
                    "inner_optimizer_semantics": "adamw",
                    "outer_optimizer_semantics": "nesterov",
                    "parameter_fragment_semantics": "synthetic_vector_fragments",
                    "learners_observed": 1,
                    "sync_rounds_completed": 1,
                    "fragments_observed": 2,
                    "max_abs_error": 0.0,
                }
                if output_artifact_path == M089R_OUTPUT_ARTIFACT_PATH
                else {
                    "tiny_real_training_smoke_status": "passed",
                    "model": "tiny-linear",
                    "steps_completed": 1,
                    "optimizer": "adamw",
                    "cpu_only": True,
                    "torch_required": False,
                    "gpu_required": False,
                    "training_attempted": True,
                    "real_training_mechanics_exercised": True,
                }
                if output_artifact_path == M093R_OUTPUT_ARTIFACT_PATH
                else None
            ),
            experiment_output_artifact_parsed_summary_persisted=(
                output_artifact_path
                in {
                    M075R_OUTPUT_ARTIFACT_PATH,
                    M077R_OUTPUT_ARTIFACT_PATH,
                    M079R_OUTPUT_ARTIFACT_PATH,
                    M081R_OUTPUT_ARTIFACT_PATH,
                    M083R_OUTPUT_ARTIFACT_PATH,
                    M085R_OUTPUT_ARTIFACT_PATH,
                    M087R_OUTPUT_ARTIFACT_PATH,
                    M089R_OUTPUT_ARTIFACT_PATH,
                    M093R_OUTPUT_ARTIFACT_PATH,
                }
            ),
            experiment_output_artifact_parsed_summary=(
                {"runtime_smoke_status": "passed"}
                if output_artifact_path == M075R_OUTPUT_ARTIFACT_PATH
                else {"synthetic_experiment_status": "passed"}
                if output_artifact_path == M077R_OUTPUT_ARTIFACT_PATH
                else {"learner_syncer_smoke_status": "passed"}
                if output_artifact_path == M079R_OUTPUT_ARTIFACT_PATH
                else {
                    "diloco_smoke_status": "passed",
                    "optimization_fidelity": "diloco_shaped_protocol_only",
                    "inner_optimizer_semantics": "synthetic_placeholder",
                    "outer_optimizer_semantics": "token_weighted_merge",
                    "parameter_fragment_semantics": "not_exercised",
                }
                if output_artifact_path == M081R_OUTPUT_ARTIFACT_PATH
                else {
                    "diloco_optimizer_smoke_status": "passed",
                    "optimization_fidelity": "optimizer_semantics_smoke",
                    "inner_optimizer_semantics": "adamw",
                    "outer_optimizer_semantics": "nesterov",
                    "parameter_fragment_semantics": "not_exercised",
                }
                if output_artifact_path == M083R_OUTPUT_ARTIFACT_PATH
                else {
                    "integrated_diloco_smoke_status": "passed",
                    "optimization_fidelity": "integrated_optimizer_protocol_smoke",
                    "inner_optimizer_semantics": "adamw",
                    "outer_optimizer_semantics": "nesterov",
                    "parameter_fragment_semantics": "not_exercised",
                }
                if output_artifact_path == M085R_OUTPUT_ARTIFACT_PATH
                else {
                    "parameter_fragment_smoke_status": "passed",
                    "parameter_fragment_semantics": "synthetic_vector_fragments",
                    "fragment_count": 2,
                    "fragment_update_check_passed": True,
                    "fragment_merge_check_passed": True,
                    "fragment_reconstruction_check_passed": True,
                    "fragment_schedule_check_passed": True,
                    "fragment_state_roundtrip_check_passed": True,
                    "per_fragment_reference_check_passed": True,
                    "global_reference_check_passed": True,
                    "max_abs_error": 0.0,
                    "overlap_semantics": "not_exercised",
                    "quantization_semantics": "not_exercised",
                }
                if output_artifact_path == M087R_OUTPUT_ARTIFACT_PATH
                else {
                    "bounded_diloco_experiment_status": "passed",
                    "optimization_fidelity": "bounded_synthetic_diloco_experiment",
                    "inner_optimizer_semantics": "adamw",
                    "outer_optimizer_semantics": "nesterov",
                    "parameter_fragment_semantics": "synthetic_vector_fragments",
                    "learners_observed": 1,
                    "sync_rounds_completed": 1,
                    "fragments_observed": 2,
                    "max_abs_error": 0.0,
                }
                if output_artifact_path == M089R_OUTPUT_ARTIFACT_PATH
                else {
                    "tiny_real_training_smoke_status": "passed",
                    "model": "tiny-linear",
                    "steps_completed": 1,
                    "optimizer": "adamw",
                    "cpu_only": True,
                    "torch_required": False,
                    "gpu_required": False,
                    "training_attempted": True,
                    "real_training_mechanics_exercised": True,
                }
                if output_artifact_path == M093R_OUTPUT_ARTIFACT_PATH
                else None
            ),
            experiment_output_artifact_parse_status=(
                "parsed_safe_runtime_smoke_artifact"
                if output_artifact_path == M075R_OUTPUT_ARTIFACT_PATH
                else "parsed_safe_synthetic_experiment_artifact"
                if output_artifact_path == M077R_OUTPUT_ARTIFACT_PATH
                else "parsed_safe_learner_syncer_smoke_artifact"
                if output_artifact_path == M079R_OUTPUT_ARTIFACT_PATH
                else "parsed_safe_diloco_smoke_artifact"
                if output_artifact_path == M081R_OUTPUT_ARTIFACT_PATH
                else "parsed_safe_diloco_optimizer_smoke_artifact"
                if output_artifact_path == M083R_OUTPUT_ARTIFACT_PATH
                else "parsed_safe_integrated_diloco_smoke_artifact"
                if output_artifact_path == M085R_OUTPUT_ARTIFACT_PATH
                else "parsed_safe_parameter_fragment_smoke_artifact"
                if output_artifact_path == M087R_OUTPUT_ARTIFACT_PATH
                else "parsed_safe_bounded_diloco_experiment_artifact"
                if output_artifact_path == M089R_OUTPUT_ARTIFACT_PATH
                else "parsed_safe_tiny_real_training_smoke_artifact"
                if output_artifact_path == M093R_OUTPUT_ARTIFACT_PATH
                else None
            ),
            experiment_output_artifact_content_capture_status=(
                "body_persisted"
                if output_artifact_path
                in {
                    M075R_OUTPUT_ARTIFACT_PATH,
                    M077R_OUTPUT_ARTIFACT_PATH,
                    M079R_OUTPUT_ARTIFACT_PATH,
                    M081R_OUTPUT_ARTIFACT_PATH,
                    M083R_OUTPUT_ARTIFACT_PATH,
                    M085R_OUTPUT_ARTIFACT_PATH,
                    M087R_OUTPUT_ARTIFACT_PATH,
                    M089R_OUTPUT_ARTIFACT_PATH,
                    M093R_OUTPUT_ARTIFACT_PATH,
                }
                else None
            ),
            stdout_sha256_prefix=_hash_text("".join(item.stage for item in stage_results))[:16],
            stage_results=stage_results,
            commands_executed=len(stage_results),
            vertical_slice_status="vertical_slice_success",
            warnings=["fake-server mode did not open an SSH socket"],
        )
    if private_key_path is None or not private_key_path.is_file():
        return LambdaRemoteVerticalSliceEvidence(
            **base_fields,
            auth_result="ssh_key_missing",
            vertical_slice_status="ssh_key_missing",
            blockers=["ssh_key_missing"],
        )
    port_ready = _wait_for_ssh_port_ready(
        host=host_discovery_result.host,
        timeout_seconds=ssh_port_ready_timeout_seconds,
        interval_seconds=ssh_port_poll_interval_seconds,
        connect_timeout_seconds=ssh_port_connect_timeout_seconds,
        checker=_default_tcp_connect_checker,
        sleep_func=time.sleep,
    )
    if not port_ready.reachable:
        return LambdaRemoteVerticalSliceEvidence(
            **base_fields,
            auth_result="ssh_port_not_reachable",
            target_host_redacted=host_discovery_result.host_redacted or "<redacted-host>",
            ssh_key_present=True,
            ssh_key_permissions_too_open=bool(private_key_path.stat().st_mode & 0o077),
            ssh_port_readiness_attempted=True,
            ssh_port_reachable=False,
            ssh_port_poll_count=port_ready.poll_count,
            ssh_port_wait_seconds=port_ready.elapsed_seconds,
            ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
            vertical_slice_status="ssh_port_not_reachable",
            blockers=["ssh_port_not_reachable"],
        )
    banner_fields: dict[str, Any] = {}
    upload_requires_banner_readiness = (
        source_bundle_path is not None or dependency_bundle_path is not None
    )
    if upload_requires_banner_readiness:
        banner_ready = _wait_for_ssh_banner_ready(
            host=host_discovery_result.host,
            timeout_seconds=ssh_banner_ready_timeout_seconds,
            interval_seconds=ssh_banner_poll_interval_seconds,
            read_timeout_seconds=ssh_banner_read_timeout_seconds,
            reader=_default_ssh_banner_reader,
            sleep_func=time.sleep,
        )
        banner_fields = {
            "ssh_banner_readiness_attempted": True,
            "ssh_banner_ready": banner_ready.ready,
            "ssh_banner_poll_count": banner_ready.poll_count,
            "ssh_banner_wait_seconds": banner_ready.elapsed_seconds,
            "ssh_banner_read_timeout_seconds": ssh_banner_read_timeout_seconds,
            "ssh_banner_prefix_observed": banner_ready.banner_prefix_observed,
        }
        if not banner_ready.ready:
            return LambdaRemoteVerticalSliceEvidence(
                **base_fields,
                probe_attempted=True,
                probe_completed=False,
                auth_result="ssh_banner_not_ready",
                target_host_redacted=host_discovery_result.host_redacted
                or "<redacted-host>",
                ssh_key_present=True,
                ssh_key_permissions_too_open=bool(private_key_path.stat().st_mode & 0o077),
                ssh_port_readiness_attempted=True,
                ssh_port_reachable=True,
                ssh_port_poll_count=port_ready.poll_count,
                ssh_port_wait_seconds=port_ready.elapsed_seconds,
                ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
                **banner_fields,
                source_bundle_upload_attempted=False,
                dependency_bundle_upload_attempted=False,
                exit_status=255,
                vertical_slice_status="ssh_banner_not_ready",
                failed_stage="ssh_banner_readiness",
                blockers=["ssh_banner_not_ready_before_upload"],
                errors=["ssh_banner_not_ready_before_upload"],
            )
    upload_stderr_capture: dict[str, Any] | None = None
    if source_bundle_path is not None:
        if not source_bundle_path.is_file():
            return LambdaRemoteVerticalSliceEvidence(
                **base_fields,
                probe_attempted=True,
                probe_completed=False,
                auth_result="source_bundle_missing",
                target_host_redacted=host_discovery_result.host_redacted
                or "<redacted-host>",
                ssh_key_present=True,
                ssh_key_permissions_too_open=bool(private_key_path.stat().st_mode & 0o077),
                ssh_port_readiness_attempted=True,
                ssh_port_reachable=True,
                ssh_port_poll_count=port_ready.poll_count,
                ssh_port_wait_seconds=port_ready.elapsed_seconds,
                ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
                **banner_fields,
                source_bundle_upload_attempted=False,
                vertical_slice_status="source_bundle_missing",
                blockers=["source_bundle_missing"],
            )
        upload_command = _real_m067r_scp_command(
            host=host_discovery_result.host,
            private_key_path=private_key_path,
            ssh_username=ssh_username,
            source_bundle_path=source_bundle_path,
            remote_bundle_path=remote_source_bundle_path,
        )
        try:
            upload_completed = subprocess.run(  # noqa: S603 - bounded safe scp argv.
                upload_command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            upload_timed_out = False
        except subprocess.TimeoutExpired as exc:
            upload_completed = subprocess.CompletedProcess(
                upload_command,
                255,
                exc.stdout or "",
                exc.stderr or "",
            )
            upload_timed_out = True
        upload_stderr_capture = _redacted_stderr_fields(
            stderr=upload_completed.stderr or "",
            private_key_path=private_key_path,
            host=host_discovery_result.host,
        )
        if upload_timed_out or upload_completed.returncode != 0:
            return LambdaRemoteVerticalSliceEvidence(
                **base_fields,
                probe_attempted=True,
                probe_completed=True,
                auth_result="source_bundle_upload_failed",
                remote_command_result="failed",
                target_host_redacted=host_discovery_result.host_redacted
                or "<redacted-host>",
                ssh_key_present=True,
                ssh_key_permissions_too_open=bool(private_key_path.stat().st_mode & 0o077),
                ssh_port_readiness_attempted=True,
                ssh_port_reachable=True,
                ssh_port_poll_count=port_ready.poll_count,
                ssh_port_wait_seconds=port_ready.elapsed_seconds,
                ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
                **banner_fields,
                source_bundle_upload_attempted=True,
                source_bundle_upload_succeeded=False,
                uploaded_bundles_count=1,
                exit_status=upload_completed.returncode,
                vertical_slice_status="source_bundle_upload_failed",
                failed_stage="source_bundle_upload",
                **upload_stderr_capture,
                errors=["source_bundle_upload_failed"],
            )
    if dependency_bundle_path is not None:
        if not dependency_bundle_path.is_file():
            return LambdaRemoteVerticalSliceEvidence(
                **base_fields,
                probe_attempted=True,
                probe_completed=False,
                auth_result="dependency_bundle_missing",
                target_host_redacted=host_discovery_result.host_redacted
                or "<redacted-host>",
                ssh_key_present=True,
                ssh_key_permissions_too_open=bool(private_key_path.stat().st_mode & 0o077),
                ssh_port_readiness_attempted=True,
                ssh_port_reachable=True,
                ssh_port_poll_count=port_ready.poll_count,
                ssh_port_wait_seconds=port_ready.elapsed_seconds,
                ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
                **banner_fields,
                source_bundle_upload_attempted=source_bundle_path is not None,
                source_bundle_upload_succeeded=source_bundle_path is not None,
                dependency_bundle_upload_attempted=False,
                uploaded_bundles_count=int(source_bundle_path is not None),
                vertical_slice_status="dependency_bundle_missing",
                blockers=["dependency_bundle_missing"],
            )
        dependency_upload_command = _real_m067r_scp_command(
            host=host_discovery_result.host,
            private_key_path=private_key_path,
            ssh_username=ssh_username,
            source_bundle_path=dependency_bundle_path,
            remote_bundle_path=M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
        )
        try:
            dependency_upload_completed = subprocess.run(  # noqa: S603
                dependency_upload_command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            dependency_upload_timed_out = False
        except subprocess.TimeoutExpired as exc:
            dependency_upload_completed = subprocess.CompletedProcess(
                dependency_upload_command,
                255,
                exc.stdout or "",
                exc.stderr or "",
            )
            dependency_upload_timed_out = True
        dependency_upload_stderr_capture = _redacted_stderr_fields(
            stderr=dependency_upload_completed.stderr or "",
            private_key_path=private_key_path,
            host=host_discovery_result.host,
        )
        if (
            dependency_upload_timed_out
            or dependency_upload_completed.returncode != 0
        ):
            return LambdaRemoteVerticalSliceEvidence(
                **base_fields,
                probe_attempted=True,
                probe_completed=True,
                auth_result="dependency_bundle_upload_failed",
                remote_command_result="failed",
                target_host_redacted=host_discovery_result.host_redacted
                or "<redacted-host>",
                ssh_key_present=True,
                ssh_key_permissions_too_open=bool(private_key_path.stat().st_mode & 0o077),
                ssh_port_readiness_attempted=True,
                ssh_port_reachable=True,
                ssh_port_poll_count=port_ready.poll_count,
                ssh_port_wait_seconds=port_ready.elapsed_seconds,
                ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
                **banner_fields,
                source_bundle_upload_attempted=source_bundle_path is not None,
                source_bundle_upload_succeeded=source_bundle_path is not None,
                dependency_bundle_upload_attempted=True,
                dependency_bundle_upload_succeeded=False,
                uploaded_bundles_count=int(source_bundle_path is not None) + 1,
                exit_status=dependency_upload_completed.returncode,
                vertical_slice_status="dependency_bundle_upload_failed",
                failed_stage="dependency_bundle_upload",
                **dependency_upload_stderr_capture,
                errors=["dependency_bundle_upload_failed"],
            )
    started_all = time.monotonic()
    stage_results: list[LambdaRemoteVerticalSliceStageResult] = []
    failed_stage: str | None = None
    exit_status: int | None = None
    stderr_aggregate = ""
    stdout_hash_material = ""
    for entry in manifest.command_entries:
        command = _real_m066r_ssh_command(
            host=host_discovery_result.host,
            private_key_path=private_key_path,
            ssh_username=ssh_username,
            argv_tokens=entry.argv_tokens,
            milestone=manifest.milestone,
        )
        started_stage = time.monotonic()
        try:
            completed = subprocess.run(  # noqa: S603 - argv is manifest-validated.
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=entry.timeout_seconds,
                check=False,
            )
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            completed = subprocess.CompletedProcess(
                command,
                255,
                exc.stdout or "",
                exc.stderr or "",
            )
            timed_out = True
        elapsed_stage = round(time.monotonic() - started_stage, 6)
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        stdout_hash_material += stdout
        stderr_aggregate += stderr
        stdout_raw = stdout.encode("utf-8", errors="replace")
        stderr_capture = _redacted_stderr_fields(
            stderr=stderr,
            private_key_path=private_key_path,
            host=host_discovery_result.host,
        )
        passed = (completed.returncode in entry.expected_success_exit_codes) and not timed_out
        if passed and entry.stage == "source_bundle_hash_check":
            if source_bundle_sha256 is not None and not stdout.strip().startswith(
                source_bundle_sha256
            ):
                passed = False
        if passed and entry.stage == "dependency_bundle_hash_check":
            if dependency_bundle_sha256 is not None and not stdout.strip().startswith(
                dependency_bundle_sha256
            ):
                passed = False
        stage_results.append(
            LambdaRemoteVerticalSliceStageResult(
                stage=entry.stage,
                command_hash=_hash_json(entry.model_dump(mode="json"))[:16],
                exact_command_redacted="<redacted-m066r-command>",
                exit_code=completed.returncode,
                timed_out=timed_out,
                stdout_redacted=f"<redacted-{entry.stage}-stdout>" if stdout else "",
                stdout_sha256_prefix=_hash_text(stdout)[:16] if stdout else None,
                stdout_truncated=len(stdout_raw) > entry.allowed_stdout_bytes,
                stderr_redacted_present=bool(stderr_capture["stderr_redacted"]),
                stderr_sha256_prefix=stderr_capture["stderr_sha256_prefix"],
                stderr_truncated=bool(stderr_capture["stderr_truncated"]),
                elapsed_seconds=elapsed_stage,
                passed=passed,
                failure_stage_if_failed=None if passed else entry.failure_stage_if_nonzero,
            )
        )
        exit_status = completed.returncode
        if not passed:
            failed_stage = entry.stage
            break
    elapsed = round(time.monotonic() - started_all, 6)
    stderr_capture = _redacted_stderr_fields(
        stderr=stderr_aggregate,
        private_key_path=private_key_path,
        host=host_discovery_result.host,
    )
    if failed_stage is None:
        status = "vertical_slice_success"
        remote_result = "succeeded"
        auth_result = "remote_vertical_slice_succeeded"
        errors: list[str] = []
        classification = None
    else:
        status = f"vertical_slice_failed_at_{failed_stage}"
        remote_result = "failed"
        classification_result = classify_ssh_failure(
            exit_code=exit_status or 255,
            stderr_redacted=stderr_capture["stderr_redacted"],
            tcp_readiness_succeeded=True,
        )
        classification = classification_result.classification
        auth_result = "remote_vertical_slice_completed_with_stage_failure"
        errors = [status, f"m066r_stage_exit_status_{exit_status}"]
    hash_verified = any(
        item.stage == "source_bundle_hash_check" and item.passed
        for item in stage_results
    )
    dependency_hash_verified = any(
        item.stage == "dependency_bundle_hash_check" and item.passed
        for item in stage_results
    )
    local_install_attempted = any(
        item.stage
        in {"dependency_install_local_only", "dependency_install_or_path_setup"}
        for item in stage_results
    )
    local_install_succeeded = any(
        item.stage
        in {"dependency_install_local_only", "dependency_install_or_path_setup"}
        and item.passed
        for item in stage_results
    )
    artifact_metadata = {
        "experiment_output_artifact_capture_attempted": False,
        "experiment_output_artifact_capture_succeeded": False,
        "experiment_output_artifact_path": None,
        "experiment_output_artifact_exists": False,
        "experiment_output_artifact_bytes": None,
        "experiment_output_artifact_sha256": None,
        "experiment_output_artifact_secret_scan_passed": None,
        "experiment_output_artifact_body_capture_attempted": False,
        "experiment_output_artifact_body_capture_succeeded": False,
        "experiment_output_artifact_body_persisted": False,
        "experiment_output_artifact_body_json": None,
        "experiment_output_artifact_parsed_summary_persisted": False,
        "experiment_output_artifact_parsed_summary": None,
        "experiment_output_artifact_parse_status": None,
        "experiment_output_artifact_content_capture_status": None,
    }
    capture_output_artifact = output_artifact_path is not None and (
        failed_stage is None
        or _stage_declares_output_artifact_path(
            manifest,
            stage=failed_stage,
            output_artifact_path=output_artifact_path,
        )
    )
    if capture_output_artifact and output_artifact_path is not None:
        artifact_metadata = _capture_remote_output_artifact_metadata(
            host=host_discovery_result.host,
            private_key_path=private_key_path,
            ssh_username=ssh_username,
            milestone=manifest.milestone,
            remote_path=output_artifact_path,
        )
        if (
            failed_stage is None
            and not artifact_metadata["experiment_output_artifact_capture_succeeded"]
        ):
            failed_stage = "experiment_output_artifact_capture"
            status = "vertical_slice_failed_at_experiment_output_artifact_capture"
            remote_result = "failed"
            auth_result = "remote_vertical_slice_completed_with_stage_failure"
            errors = [status]
    return LambdaRemoteVerticalSliceEvidence(
        **base_fields,
        probe_attempted=True,
        probe_completed=True,
        probe_passed=True,
        auth_result=auth_result,
        remote_command_attempted=True,
        remote_command_result=remote_result,
        source_bundle_upload_attempted=source_bundle_path is not None,
        source_bundle_upload_succeeded=source_bundle_path is not None,
        source_bundle_hash_verified=(
            hash_verified if source_bundle_path is not None else False
        ),
        dependency_bundle_upload_attempted=dependency_bundle_path is not None,
        dependency_bundle_upload_succeeded=dependency_bundle_path is not None,
        dependency_bundle_hash_verified=(
            dependency_hash_verified if dependency_bundle_path is not None else False
        ),
        uploaded_bundles_count=int(source_bundle_path is not None)
        + int(dependency_bundle_path is not None),
        local_dependency_install_attempted=local_install_attempted,
        local_dependency_install_succeeded=local_install_succeeded,
        **artifact_metadata,
        target_host_redacted=host_discovery_result.host_redacted or "<redacted-host>",
        ssh_key_present=True,
        ssh_key_permissions_too_open=bool(private_key_path.stat().st_mode & 0o077),
        ssh_port_readiness_attempted=True,
        ssh_port_reachable=True,
        ssh_port_poll_count=port_ready.poll_count,
        ssh_port_wait_seconds=port_ready.elapsed_seconds,
        ssh_port_connect_timeout_seconds=ssh_port_connect_timeout_seconds,
        **banner_fields,
        exit_status=exit_status,
        ssh_failure_classification=classification,
        elapsed_seconds=elapsed,
        commands_executed=len(stage_results),
        stage_results=stage_results,
        failed_stage=failed_stage,
        vertical_slice_status=status,
        stdout_sha256_prefix=(
            _hash_text(stdout_hash_material)[:16] if stdout_hash_material else None
        ),
        stdout_truncated=any(item.stdout_truncated for item in stage_results),
        stdout_redaction_patterns_applied=["m066r_stage_stdout_redacted"],
        **stderr_capture,
        errors=errors,
    )


def _capture_remote_output_artifact_metadata(
    *,
    host: str,
    private_key_path: Path,
    ssh_username: str,
    milestone: str,
    remote_path: str,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "experiment_output_artifact_capture_attempted": True,
        "experiment_output_artifact_capture_succeeded": False,
        "experiment_output_artifact_path": remote_path,
        "experiment_output_artifact_exists": False,
        "experiment_output_artifact_bytes": None,
        "experiment_output_artifact_sha256": None,
        "experiment_output_artifact_secret_scan_passed": None,
        "experiment_output_artifact_body_capture_attempted": False,
        "experiment_output_artifact_body_capture_succeeded": False,
        "experiment_output_artifact_body_persisted": False,
        "experiment_output_artifact_body_json": None,
        "experiment_output_artifact_parsed_summary_persisted": False,
        "experiment_output_artifact_parsed_summary": None,
        "experiment_output_artifact_parse_status": None,
        "experiment_output_artifact_content_capture_status": None,
    }
    with tempfile.TemporaryDirectory(
        prefix=f"decodilo-{milestone.lower()}-artifact-"
    ) as tmpdir:
        local_path = Path(tmpdir) / Path(remote_path).name
        command = _real_remote_artifact_scp_download_command(
            host=host,
            private_key_path=private_key_path,
            ssh_username=ssh_username,
            remote_path=remote_path,
            local_path=local_path,
        )
        try:
            completed = subprocess.run(  # noqa: S603 - bounded safe scp argv.
                command,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return metadata
        if completed.returncode != 0 or not local_path.is_file():
            return metadata
        metadata.update(
            {
                "experiment_output_artifact_capture_succeeded": True,
                "experiment_output_artifact_exists": True,
                "experiment_output_artifact_bytes": local_path.stat().st_size,
                "experiment_output_artifact_sha256": _sha256_file(local_path),
                "experiment_output_artifact_secret_scan_passed": (
                    _remote_artifact_secret_scan_passed(local_path)
                ),
            }
        )
        if str(PurePosixPath(remote_path)).startswith("/tmp/"):
            from decodilo.lambda_cloud.remote_vslice_manifest_artifact_capture import (
                build_manifest_declared_artifact_capture_from_local_file,
            )

            declared_capture = build_manifest_declared_artifact_capture_from_local_file(
                declared_remote_path=remote_path,
                local_artifact_path=local_path,
                manifest_declared_paths=[remote_path],
            )
            metadata.update(declared_capture.evidence_fields())
    return metadata


def _remote_artifact_secret_scan_passed(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    patterns = [
        re.compile(r"Authorization:\s*\S+", re.IGNORECASE),
        re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{16,}"),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"API[_-]?KEY\s*[:=]\s*(?!<|redacted)", re.IGNORECASE),
        re.compile(r"password\s*[:=]\s*(?!<|redacted)", re.IGNORECASE),
    ]
    return not any(pattern.search(text) for pattern in patterns)


class _SSHBannerReadiness(BaseModel):
    model_config = ConfigDict(frozen=True)

    ready: bool
    poll_count: int
    elapsed_seconds: float
    banner_prefix_observed: bool = False


def _wait_for_ssh_banner_ready(
    *,
    host: str,
    timeout_seconds: float,
    interval_seconds: float,
    read_timeout_seconds: float,
    reader: Callable[[str, int, float], str | None],
    sleep_func: Callable[[float], None],
) -> _SSHBannerReadiness:
    started = time.monotonic()
    deadline = started + max(0.0, timeout_seconds)
    poll_count = 0
    while True:
        poll_count += 1
        banner = reader(host, 22, read_timeout_seconds) or ""
        if banner.startswith("SSH-2.0-"):
            return _SSHBannerReadiness(
                ready=True,
                poll_count=poll_count,
                elapsed_seconds=round(time.monotonic() - started, 6),
                banner_prefix_observed=True,
            )
        now = time.monotonic()
        if now >= deadline:
            return _SSHBannerReadiness(
                ready=False,
                poll_count=poll_count,
                elapsed_seconds=round(now - started, 6),
                banner_prefix_observed=False,
            )
        sleep_func(min(interval_seconds, max(0.0, deadline - now)))


def _default_ssh_banner_reader(
    host: str,
    port: int,
    timeout_seconds: float,
) -> str | None:
    socket = importlib.import_module("socket")
    try:
        with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
            sock.settimeout(timeout_seconds)
            data = sock.recv(256)
    except OSError:
        return None
    return data.decode("utf-8", errors="replace").strip()


def _validate_command_entry(
    entry: LambdaRemoteVerticalSliceCommandEntry,
    *,
    milestone: str = M066R_MILESTONE,
) -> list[str]:
    blockers: list[str] = []
    command_text = entry.exact_command
    if "\n" in command_text or "\r" in command_text:
        blockers.append(f"forbidden_shell_newline_in_{entry.stage}")
    try:
        rendered = render_lambda_remote_vertical_slice_argv(entry.argv_tokens)
    except ValueError:
        blockers.append(f"invalid_argv_tokens_in_{entry.stage}")
        rendered = ""
    if rendered and command_text != rendered:
        blockers.append(f"raw_shell_string_not_safe_rendered_in_{entry.stage}")
    allowed = {
        tuple(argv)
        for _, argv in (
            M067R_ALLOWED_COMMANDS
            if milestone
            in {
                M067R_MILESTONE,
                M068R_MILESTONE,
                M071R_MILESTONE,
                M073R_MILESTONE,
                M075R_MILESTONE,
                M077R_MILESTONE,
                M079R_MILESTONE,
                M081R_MILESTONE,
                M083R_MILESTONE,
                M085R_MILESTONE,
                M087R_MILESTONE,
                M089R_MILESTONE,
                M093R_MILESTONE,
            }
            else M066R_DEFAULT_COMMANDS
        )
    }
    tuple_allowed = tuple(entry.argv_tokens) in allowed
    if _is_dependency_bundle_milestone(milestone) and _m068r_command_allowed(
        entry.argv_tokens,
        milestone=milestone,
    ):
        tuple_allowed = True
    if not tuple_allowed:
        blockers.append(f"unapproved_command_stage_{entry.stage}")
    for index, token in enumerate(entry.argv_tokens):
        lowered = token.lower()
        if any(pattern in token for pattern in (";", "|", ">", "<", "$(", "`", "&")):
            blockers.append(f"forbidden_shell_metacharacter_in_{entry.stage}")
        if (
            milestone
            in {
                M067R_MILESTONE,
                M068R_MILESTONE,
                M071R_MILESTONE,
                M073R_MILESTONE,
                M075R_MILESTONE,
                M077R_MILESTONE,
                M079R_MILESTONE,
                M081R_MILESTONE,
                M083R_MILESTONE,
                M085R_MILESTONE,
                M087R_MILESTONE,
                M089R_MILESTONE,
                M093R_MILESTONE,
            }
            and lowered == "-c"
            and index > 0
            and entry.argv_tokens[index - 1] in {"python", "python3"}
        ):
            blockers.append(f"forbidden_python_inline_code_in_{entry.stage}")
        if lowered in FORBIDDEN_TOKENS:
            if lowered in {"pip", "pip3"} and _is_dependency_bundle_milestone(
                milestone
            ):
                if not _m068r_pip_install_is_local_only(entry.argv_tokens):
                    blockers.append(
                        f"forbidden_internet_package_install_token_in_{entry.stage}"
                    )
            elif lowered in {"pip", "pip3", "conda", "apt", "apt-get"}:
                blockers.append(f"forbidden_package_install_token_in_{entry.stage}")
            elif lowered in {"curl", "wget", "download", "git", "clone", "docker"}:
                blockers.append(f"forbidden_download_token_in_{entry.stage}")
            elif lowered in {"scp", "sftp", "rsync"}:
                blockers.append(f"forbidden_file_transfer_token_in_{entry.stage}")
            elif lowered in {"nohup", "tmux", "screen"}:
                blockers.append(f"forbidden_background_process_token_in_{entry.stage}")
            elif lowered in {"sh", "bash", "zsh", "fish"}:
                blockers.append(f"forbidden_arbitrary_shell_token_in_{entry.stage}")
            else:
                blockers.append(f"forbidden_token_{lowered}_in_{entry.stage}")
    return blockers


def _m068r_command_allowed(
    argv_tokens: list[str],
    *,
    milestone: str = M068R_MILESTONE,
) -> bool:
    if not argv_tokens:
        return False
    if argv_tokens in [list(argv) for _, argv in M067R_ALLOWED_COMMANDS]:
        return True
    if argv_tokens[:4] == ["mkdir", "-p", "/tmp/decodilo-deps"]:
        return True
    if argv_tokens[:4] == ["mkdir", "-p", "/tmp/decodilo-runtime"]:
        return True
    if argv_tokens == [
        "sha256sum",
        M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
    ]:
        return True
    if milestone in {
        M073R_MILESTONE,
        M075R_MILESTONE,
        M077R_MILESTONE,
        M079R_MILESTONE,
        M081R_MILESTONE,
        M083R_MILESTONE,
        M085R_MILESTONE,
        M087R_MILESTONE,
        M089R_MILESTONE,
        M093R_MILESTONE,
    } and argv_tokens == [
        "sha256sum",
        _remote_source_bundle_path_for_milestone(milestone),
    ]:
        return True
    if milestone in {
        M073R_MILESTONE,
        M075R_MILESTONE,
        M077R_MILESTONE,
        M079R_MILESTONE,
        M081R_MILESTONE,
        M083R_MILESTONE,
        M085R_MILESTONE,
        M087R_MILESTONE,
        M089R_MILESTONE,
        M093R_MILESTONE,
    } and argv_tokens[:5] == [
        "tar",
        "-xzf",
        _remote_source_bundle_path_for_milestone(milestone),
        "-C",
        M067R_REMOTE_EXTRACT_DIR,
    ]:
        return True
    if argv_tokens[:5] == [
        "tar",
        "-xzf",
        M068R_REMOTE_DEPENDENCY_BUNDLE_PATH,
        "-C",
        M068R_REMOTE_DEPENDENCY_EXTRACT_DIR,
    ]:
        return True
    if _m068r_pip_install_is_local_only(argv_tokens):
        return True
    if len(argv_tokens) >= 4 and argv_tokens[0] == "env":
        py_path = next(
            (
                token
                for token in argv_tokens[1:]
                if token.startswith("PYTHONPATH=/tmp/decodilo-runtime:")
                or token.startswith("PYTHONPATH=/tmp/decodilo-deps:")
            ),
            None,
        )
        if py_path is None:
            return False
        command_tail = [token for token in argv_tokens[1:] if token != py_path]
        m068r_tail = [
            ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
            ["python3", "-m", "decodilo.cli", "--help"],
            ["python3", "-m", "decodilo.cli", "dev", "test-profile-summary"],
            [
                "python3",
                "-m",
                "decodilo.cli",
                "dev",
                "ci-profile-report",
                "--out",
                "/tmp/decodilo-remote-ci-profile-report.json",
            ],
        ]
        if milestone == M073R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M073R_TINY_SMOKE_COMMAND[2:]),
            ]
        if milestone == M075R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M075R_RUNTIME_SMOKE_COMMAND[2:]),
            ]
        if milestone == M077R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M077R_SYNTHETIC_EXPERIMENT_COMMAND[2:]),
            ]
        if milestone == M079R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M079R_LEARNER_SYNCER_SMOKE_COMMAND[2:]),
            ]
        if milestone == M081R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M081R_DILOCO_SMOKE_COMMAND[2:]),
            ]
        if milestone == M083R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M083R_DILOCO_OPTIMIZER_SMOKE_COMMAND[2:]),
            ]
        if milestone == M085R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M085R_INTEGRATED_DILOCO_SMOKE_COMMAND[2:]),
            ]
        if milestone == M087R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M087R_PARAMETER_FRAGMENT_SMOKE_COMMAND[2:]),
            ]
        if milestone == M089R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M089R_BOUNDED_DILOCO_EXPERIMENT_COMMAND[2:]),
            ]
        if milestone == M093R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M093R_TINY_REAL_TRAINING_SMOKE_COMMAND[2:]),
            ]
        if milestone == M071R_MILESTONE:
            return command_tail in [
                ["python3", M067R_REMOTE_IMPORT_PROBE_PATH],
                ["python3", "-m", "decodilo.cli", "--help"],
                list(M071R_FIRST_EXPERIMENT_COMMAND[2:]),
            ]
        return command_tail in m068r_tail
    return False


def _m068r_pip_install_is_local_only(argv_tokens: list[str]) -> bool:
    if argv_tokens[:4] != ["python3", "-m", "pip", "install"]:
        return False
    if "--no-index" not in argv_tokens:
        return False
    if "--target" not in argv_tokens:
        return False
    target_index = argv_tokens.index("--target")
    if target_index + 1 >= len(argv_tokens):
        return False
    if argv_tokens[target_index + 1] != "/tmp/decodilo-runtime":
        return False
    local_sources: list[str] = []
    for flag in ("--find-links", "-f"):
        while flag in argv_tokens:
            index = argv_tokens.index(flag)
            if index + 1 >= len(argv_tokens):
                return False
            local_sources.append(argv_tokens[index + 1])
            argv_tokens = argv_tokens[:index] + argv_tokens[index + 2 :]
    if not local_sources or any(not source.startswith("/tmp/") for source in local_sources):
        return False
    forbidden_networkish = {"http://", "https://", "ftp://"}
    return not any(
        any(str(token).startswith(prefix) for prefix in forbidden_networkish)
        for token in argv_tokens
    )


def _select_candidate(
    discovery: LambdaLiveDiscoveryReport,
    price_snapshot: PriceSnapshot,
    max_budget: float,
    planned_runtime_minutes: int,
    safety_buffer_multiplier: float,
):
    live_items = [
        item
        for item in discovery.instance_types
        if item.regions and (item.name or item.instance_type_id)
    ]
    preferred = next(
        (
            item
            for item in live_items
            if (
                item.name == M056_SELECTED_CANDIDATE
                or item.instance_type_id == M056_SELECTED_CANDIDATE
            )
            and M056_SELECTED_REGION in item.regions
        ),
        None,
    )
    candidates = [preferred] if preferred is not None else live_items
    priced: list[tuple[float, Any, SnapshotPriceRecord | None]] = []
    for item in candidates:
        if item is None:
            continue
        record = _find_price_record(price_snapshot, item.name or item.instance_type_id)
        price = (
            record.price_per_instance_hour
            if record is not None
            else item.price_per_hour
        )
        if price is None:
            continue
        estimated = round(price * planned_runtime_minutes / 60, 8)
        buffered = round(estimated * safety_buffer_multiplier, 8)
        if buffered < max_budget:
            priced.append((price, item, record))
    if not priced:
        return None
    _, item, record = min(priced, key=lambda value: value[0])
    shape = item.name or item.instance_type_id
    region = (
        M056_SELECTED_REGION
        if shape == M056_SELECTED_CANDIDATE and M056_SELECTED_REGION in item.regions
        else item.regions[0]
    )
    price_per_hour = record.price_per_instance_hour if record is not None else item.price_per_hour
    estimated = round(price_per_hour * planned_runtime_minutes / 60, 8)
    buffered = round(estimated * safety_buffer_multiplier, 8)
    gpu_type = record.gpu_type if record is not None else item.gpu_type
    gpus = record.gpus_per_instance if record is not None else item.gpus
    source = (
        "fresh_live_read_only_instance_types_preferred_gpu_1x_a10"
        if shape == M056_SELECTED_CANDIDATE and region == M056_SELECTED_REGION
        else "fresh_live_read_only_instance_types_cheapest_safe_substitute"
    )
    return shape, region, source, gpu_type, gpus, price_per_hour, estimated, buffered


def _find_price_record(
    price_snapshot: PriceSnapshot,
    shape: str,
) -> SnapshotPriceRecord | None:
    return next(
        (
            record
            for record in price_snapshot.records
            if record.provider == "lambda" and record.instance_type == shape
        ),
        None,
    )


def _real_m066r_ssh_command(
    *,
    host: str,
    private_key_path: Path,
    ssh_username: str,
    argv_tokens: list[str],
    milestone: str = M066R_MILESTONE,
) -> list[str]:
    if _validate_command_entry(
        LambdaRemoteVerticalSliceCommandEntry(
            stage="runtime_validation",
            exact_command=render_lambda_remote_vertical_slice_argv(argv_tokens),
            argv_tokens=argv_tokens,
            failure_stage_if_nonzero="runtime_validation",
        ),
        milestone=milestone,
    ):
        raise ValueError("M066R command contains forbidden tokens")
    rendered_remote_command = render_lambda_remote_vertical_slice_argv(argv_tokens)
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "RequestTTY=no",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ForwardX11=no",
        "-o",
        "PermitLocalCommand=no",
        "-o",
        "ControlMaster=no",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={_isolated_known_hosts_path(host)}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "NumberOfPasswordPrompts=0",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ConnectionAttempts=1",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=1",
        "-T",
        "-i",
        str(private_key_path),
        f"{ssh_username}@{host}",
        rendered_remote_command,
    ]


def _real_m067r_scp_command(
    *,
    host: str,
    private_key_path: Path,
    ssh_username: str,
    source_bundle_path: Path,
    remote_bundle_path: str = M067R_REMOTE_BUNDLE_PATH,
) -> list[str]:
    return [
        "scp",
        "-o",
        "BatchMode=yes",
        "-o",
        "RequestTTY=no",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ForwardX11=no",
        "-o",
        "PermitLocalCommand=no",
        "-o",
        "ControlMaster=no",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={_isolated_known_hosts_path(host)}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "NumberOfPasswordPrompts=0",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ConnectionAttempts=1",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=1",
        "-i",
        str(private_key_path),
        str(source_bundle_path),
        f"{ssh_username}@{host}:{remote_bundle_path}",
    ]


def _real_remote_artifact_scp_download_command(
    *,
    host: str,
    private_key_path: Path,
    ssh_username: str,
    remote_path: str,
    local_path: Path,
) -> list[str]:
    if remote_path not in {
        M071R_OUTPUT_ARTIFACT_PATH,
        M073R_OUTPUT_ARTIFACT_PATH,
        M075R_OUTPUT_ARTIFACT_PATH,
        M077R_OUTPUT_ARTIFACT_PATH,
        M079R_OUTPUT_ARTIFACT_PATH,
        M081R_OUTPUT_ARTIFACT_PATH,
        M083R_OUTPUT_ARTIFACT_PATH,
        M085R_OUTPUT_ARTIFACT_PATH,
        M087R_OUTPUT_ARTIFACT_PATH,
        M089R_OUTPUT_ARTIFACT_PATH,
        M093R_OUTPUT_ARTIFACT_PATH,
    }:
        raise ValueError("artifact capture only allows approved output paths")
    return [
        "scp",
        "-o",
        "BatchMode=yes",
        "-o",
        "RequestTTY=no",
        "-o",
        "ClearAllForwardings=yes",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ForwardX11=no",
        "-o",
        "PermitLocalCommand=no",
        "-o",
        "ControlMaster=no",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        f"UserKnownHostsFile={_isolated_known_hosts_path(host)}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "NumberOfPasswordPrompts=0",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "ConnectionAttempts=1",
        "-o",
        "ServerAliveInterval=5",
        "-o",
        "ServerAliveCountMax=1",
        "-i",
        str(private_key_path),
        f"{ssh_username}@{host}:{remote_path}",
        str(local_path),
    ]


def _collect_source_bundle_files(root: Path) -> tuple[list[Path], list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    candidates: list[Path] = []
    include_roots = [
        root / "src",
        root / "pyproject.toml",
        root / "tools" / "remote_probe",
    ]
    for include in include_roots:
        if include.is_file():
            candidates.append(include)
        elif include.is_dir():
            for path in include.rglob("*"):
                if path.is_file():
                    candidates.append(path)
        else:
            blockers.append(f"missing_required_bundle_input_{include.name}")
    files: list[Path] = []
    for path in sorted(candidates):
        rel = path.relative_to(root)
        rel_text = rel.as_posix()
        if _bundle_member_forbidden(rel_text):
            warnings.append(f"excluded_forbidden_path:{rel_text}")
            continue
        size = path.stat().st_size
        if size > MAX_SOURCE_BUNDLE_FILE_BYTES:
            blockers.append(f"large_file_{rel_text}")
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            blockers.append(f"non_text_file_{rel_text}")
            continue
        secret_hits = _secret_value_hits(content)
        if secret_hits:
            blockers.extend(f"secret_{hit}_in_{rel_text}" for hit in secret_hits)
            continue
        files.append(path)
    if not any(path.name == "__init__.py" and "decodilo" in path.parts for path in files):
        blockers.append("decodilo_package_init_missing_from_bundle")
    return files, blockers, warnings


def _bundle_member_forbidden(name: str) -> bool:
    parts = set(Path(name).parts)
    if parts & {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "node_modules",
    }:
        return True
    basename = Path(name).name
    if basename == ".env" or basename.startswith(".env."):
        return True
    if "lambda" in basename.lower() and "report" in basename.lower():
        return True
    return basename.endswith(
        (
            ".pyc",
            ".pyo",
            ".pem",
            ".key",
            ".ppk",
            ".pt",
            ".pth",
            ".safetensors",
            ".bin",
            ".ckpt",
            ".parquet",
            ".sqlite",
            ".db",
        )
    )


def _secret_value_hits(content: str) -> list[str]:
    hits: list[str] = []
    for name, pattern in SECRET_VALUE_REGEXES.items():
        if pattern.search(content):
            hits.append(name)
    return hits


def load_lambda_remote_vertical_slice_policy(
    path: str | Path,
) -> LambdaRemoteVerticalSlicePolicy:
    return LambdaRemoteVerticalSlicePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_remote_vertical_slice_command_manifest(
    path: str | Path,
) -> LambdaRemoteVerticalSliceCommandManifest:
    return LambdaRemoteVerticalSliceCommandManifest.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_remote_vertical_slice_manifest_validation(
    path: str | Path,
) -> LambdaRemoteVerticalSliceManifestValidation:
    return LambdaRemoteVerticalSliceManifestValidation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_remote_source_bundle_manifest(
    path: str | Path,
) -> LambdaRemoteSourceBundleManifest:
    return LambdaRemoteSourceBundleManifest.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_remote_source_bundle_validation(
    path: str | Path,
) -> LambdaRemoteSourceBundleValidation:
    return LambdaRemoteSourceBundleValidation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_remote_vertical_slice_execution_plan(
    path: str | Path,
) -> LambdaRemoteVerticalSliceExecutionPlan:
    return LambdaRemoteVerticalSliceExecutionPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_remote_vertical_slice_gate_check(
    path: str | Path,
) -> LambdaRemoteVerticalSliceGateCheck:
    return LambdaRemoteVerticalSliceGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_remote_vertical_slice_one_shot_arming(
    path: str | Path,
) -> LambdaRemoteVerticalSliceOneShotArming:
    return LambdaRemoteVerticalSliceOneShotArming.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def load_lambda_remote_vertical_slice_reviewer_bridge(
    path: str | Path,
) -> LambdaRemoteVerticalSliceReviewerBridge:
    return LambdaRemoteVerticalSliceReviewerBridge.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_vertical_slice_policy(
    path: str | Path,
    report: LambdaRemoteVerticalSlicePolicy,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_remote_vertical_slice_command_manifest(
    path: str | Path,
    report: LambdaRemoteVerticalSliceCommandManifest,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_remote_vertical_slice_manifest_validation(
    path: str | Path,
    report: LambdaRemoteVerticalSliceManifestValidation,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_remote_source_bundle_manifest(
    path: str | Path,
    report: LambdaRemoteSourceBundleManifest,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_remote_source_bundle_validation(
    path: str | Path,
    report: LambdaRemoteSourceBundleValidation,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_remote_vertical_slice_execution_plan(
    path: str | Path,
    report: LambdaRemoteVerticalSliceExecutionPlan,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_remote_vertical_slice_gate_check(
    path: str | Path,
    report: LambdaRemoteVerticalSliceGateCheck,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_remote_vertical_slice_one_shot_arming(
    path: str | Path,
    report: LambdaRemoteVerticalSliceOneShotArming,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_remote_vertical_slice_reviewer_bridge(
    path: str | Path,
    report: LambdaRemoteVerticalSliceReviewerBridge,
) -> None:
    _write_json(path, report.to_json())


def write_lambda_remote_vertical_slice_evidence(
    path: str | Path,
    report: LambdaRemoteVerticalSliceEvidence,
) -> None:
    _write_json(path, report.to_json())


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _hash_json(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


def _write_json(path: str | Path, text: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
