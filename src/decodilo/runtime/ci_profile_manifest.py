"""Typed CI/test profile manifest for local development and CI shards."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

QUICK_EXPRESSION = (
    "quick and not slow and not soak and not perf and not integration and not lifecycle "
    "and not hardware_optional and not lambda_live and not lambda_real_mutation "
    "and not subprocess_heavy and not launch_history_heavy"
)
OLD_QUICK_EXPRESSION = (
    "not slow and not soak and not perf and not integration and not lifecycle "
    "and not hardware_optional"
)
LAMBDA_OFFLINE_EXPRESSION = "lambda_offline and not lambda_live and not lambda_real_mutation"
RUNTIME_LOCAL_EXPRESSION = "runtime_local and not lambda_live and not lambda_real_mutation"
TORCH_OPTIONAL_EXPRESSION = "torch_optional"
UNIT_EXPRESSION = (
    "unit and not integration and not subprocess_heavy and not lambda_live "
    "and not lambda_real_mutation and not torch_optional"
)

CI_PROFILE_MARKERS = (
    "unit",
    "quick",
    "lambda_offline",
    "lambda_live",
    "lambda_real_mutation",
    "subprocess_heavy",
    "runtime_local",
    "cloud",
    "cloud_fake",
    "cloud_manual",
    "launch_history_heavy",
    "flaky_policy",
    "integration",
    "slow",
    "soak",
    "perf",
    "torch_optional",
    "cloud_disabled",
    "storage",
    "replay",
    "runtime",
    "lifecycle",
    "hardware_optional",
)

QUICK_TEST_FILES = frozenset(
    {
        "test_retry_policy.py",
        "test_content_addressed_storage.py",
        "test_event_replay.py",
        "test_replay_index.py",
        "test_price_parser.py",
        "test_price_freshness.py",
        "test_budget_guard.py",
        "test_numpy_convex_trainer.py",
        "test_trainer_interface_contract.py",
        "test_trainer_state_codec.py",
        "test_lambda_mutation_guard.py",
        "test_lambda_no_live_calls_in_tests.py",
        "test_lambda_http_response_capture.py",
        "test_lambda_lifecycle_smoke_success_record.py",
        "test_lambda_capacity_history_aware_selector.py",
        "test_lambda_capacity_selected_execution_gate_check.py",
        "test_cloud_still_disabled_m047.py",
        "test_ci_profile_manifest.py",
        "test_ci_profile_marker_coverage.py",
        "test_ci_profile_quick_smoke.py",
        "test_ci_profile_no_live_lambda.py",
        "test_ci_profile_flake_policy.py",
    }
)

SUBPROCESS_HEAVY_PATTERNS = (
    "_cli",
    "cli_",
    "live_discover",
    "local_process",
    "multiprocess",
    "fake_server",
    "server",
    "subprocess",
    "real_quick",
)
LAUNCH_HISTORY_HEAVY_PATTERNS = (
    "_m029",
    "_m030",
    "_m031",
    "_m032",
    "_m033",
    "_m034",
    "_m035",
    "_m036",
    "_m037",
    "_m038",
    "_m039",
    "_m040",
    "_m041",
    "_m043",
    "_m044",
    "_m045",
    "_m046",
)


class CiProfile(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    marker_expression: str
    pytest_command: str
    manual_only: bool = False
    target_seconds: float | None = None


class CiProfileManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: int = 1
    profiles: list[CiProfile]
    markers: list[str]
    quick_test_files: list[str]
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_no_launch_flags(self) -> CiProfileManifest:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("CI profile manifest cannot enable launch or mutation")
        return self

    def by_name(self) -> dict[str, CiProfile]:
        return {profile.name: profile for profile in self.profiles}

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_ci_profile_manifest() -> CiProfileManifest:
    profiles = [
        CiProfile(
            name="unit",
            description=(
                "Pure unit tests without subprocess-heavy runtime, Lambda live, "
                "credentials, or torch."
            ),
            marker_expression=UNIT_EXPRESSION,
            pytest_command=f'pytest -q -m "{UNIT_EXPRESSION}"',
            target_seconds=30.0,
        ),
        CiProfile(
            name="quick",
            description=(
                "Default development confidence suite with representative safety "
                "and core checks."
            ),
            marker_expression=QUICK_EXPRESSION,
            pytest_command=f'pytest -q -m "{QUICK_EXPRESSION}"',
            target_seconds=60.0,
        ),
        CiProfile(
            name="lambda_offline",
            description=(
                "Lambda offline, fake, and fixture tests; no live Lambda calls "
                "or credentials."
            ),
            marker_expression=LAMBDA_OFFLINE_EXPRESSION,
            pytest_command=f'pytest -q -m "{LAMBDA_OFFLINE_EXPRESSION}"',
        ),
        CiProfile(
            name="runtime_local",
            description="Local runtime and multiprocess tests; no cloud calls.",
            marker_expression=RUNTIME_LOCAL_EXPRESSION,
            pytest_command=f'pytest -q -m "{RUNTIME_LOCAL_EXPRESSION}"',
        ),
        CiProfile(
            name="lifecycle",
            description="Lifecycle stress, compaction, GC, replay, and recovery tests.",
            marker_expression="lifecycle",
            pytest_command='pytest -q -m "lifecycle"',
        ),
        CiProfile(
            name="perf",
            description="Performance harness and benchmark tests.",
            marker_expression="perf",
            pytest_command='pytest -q -m "perf"',
        ),
        CiProfile(
            name="torch_optional",
            description="Optional torch tests when torch is installed.",
            marker_expression=TORCH_OPTIONAL_EXPRESSION,
            pytest_command=(
                "pytest tests/test_torch_causal_lm_optional.py "
                "tests/test_torch_runtime_local_optional.py -q"
            ),
        ),
        CiProfile(
            name="full",
            description=(
                "Everything except tests requiring real live credentials or "
                "explicit operator action."
            ),
            marker_expression="",
            pytest_command="pytest -q",
        ),
        CiProfile(
            name="live_readonly_manual",
            description="Manual-only real Lambda read-only checks; never default.",
            marker_expression="lambda_live and not lambda_real_mutation",
            pytest_command='pytest -q -m "lambda_live and not lambda_real_mutation"',
            manual_only=True,
        ),
        CiProfile(
            name="real_mutation_manual",
            description=(
                "Manual-only placeholder for real mutation; real mutation belongs "
                "in CLI/operator flow."
            ),
            marker_expression="lambda_real_mutation",
            pytest_command='pytest -q -m "lambda_real_mutation"',
            manual_only=True,
        ),
    ]
    return CiProfileManifest(
        profiles=profiles,
        markers=sorted(CI_PROFILE_MARKERS),
        quick_test_files=sorted(QUICK_TEST_FILES),
    )


def classify_test_file(path: str | Path) -> set[str]:
    name = Path(path).name
    stem = Path(path).stem
    markers: set[str] = set()
    lower = name.lower()
    if name in QUICK_TEST_FILES:
        markers.add("quick")
    if lower.startswith(("test_lambda_", "test_cloud_")):
        markers.update({"lambda_offline", "cloud"})
    if "fake" in lower and ("lambda" in lower or "cloud" in lower):
        markers.add("cloud_fake")
    if "manual" in lower:
        markers.add("cloud_manual")
    if lower.startswith("test_torch_"):
        markers.add("torch_optional")
    if (
        "runtime" in lower
        or "multiprocess" in lower
        or "local_process" in lower
        or lower.startswith("test_live_chunked")
        or lower.startswith("test_live_binary_chunked")
    ):
        markers.add("runtime_local")
    if any(pattern in stem for pattern in SUBPROCESS_HEAVY_PATTERNS):
        markers.add("subprocess_heavy")
    if any(pattern in stem for pattern in LAUNCH_HISTORY_HEAVY_PATTERNS):
        markers.add("launch_history_heavy")
    return markers


def write_ci_profile_manifest(path: str | Path, manifest: CiProfileManifest) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(manifest.to_json(), encoding="utf-8")


def load_ci_profile_manifest(path: str | Path) -> CiProfileManifest:
    return CiProfileManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))
