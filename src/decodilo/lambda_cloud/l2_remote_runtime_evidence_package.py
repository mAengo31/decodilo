"""Offline evidence package for Lambda L2 remote split learner/syncer runtime."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

_NUMERIC_TOLERANCE = 1e-9
_SECRET_NEEDLES = (
    "lambda_api_key=",
    "lambda_ssh_key=",
    "-----begin ",
    "jupyter token",
    "jupyter_token",
    "authorization: bearer",
    "authorization: basic",
)


class LambdaL2RemoteRuntimeEvidencePackage(BaseModel):
    """Validated summary for the Lambda L2 remote multi-instance proof."""

    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "Lambda-L2"
    evidence_complete: bool
    lambda_l2_remote_runtime_passed: bool
    run_id: str | None = None
    remote_instance_count: int = 0
    remote_process_roles: list[str] = Field(default_factory=list)
    distinct_role_instances: bool = False
    network_path: str | None = None
    committed_sync_rounds: int = 0
    final_global_version: int = 0
    accepted_updates: int = 0
    useful_tokens_accepted: int = 0
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    pseudo_gradient_numeric_check_passed: bool = False
    pseudo_gradient_numeric_rounds_checked: int = 0
    independent_nesterov_max_abs_error: float | None = None
    checkpoint_outer_optimizer_step: int | None = None
    checkpoint_velocity_max_abs_error: float | None = None
    learner_artifacts_present: list[str] = Field(default_factory=list)
    final_instance_count: int | None = None
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    missing_items: list[str] = Field(default_factory=list)
    secret_scan_passed: bool = False
    secret_scan_findings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    billable_action_performed: bool = True
    evidence_package_builder_billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    production_scale_ready: bool = False
    pathway_operation_layer_ready: bool = False

    @model_validator(mode="after")
    def _validate_boundaries(self) -> LambdaL2RemoteRuntimeEvidencePackage:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("Lambda L2 evidence package cannot enable launch")
        if self.production_scale_ready:
            raise ValueError("Lambda L2 evidence package cannot claim production scale")
        if self.pathway_operation_layer_ready:
            raise ValueError("Lambda L2 evidence package cannot claim Pathway readiness")
        if self.evidence_complete and (self.blockers or self.missing_items):
            raise ValueError("complete evidence package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_l2_remote_runtime_evidence_package_from_dir(
    evidence_dir: str | Path,
) -> LambdaL2RemoteRuntimeEvidencePackage:
    root = Path(evidence_dir)
    required = [
        root / "layout.json",
        root / "termination_safety.json",
        root / "syncer" / "events.jsonl",
        root / "syncer" / "syncer_checkpoint.json",
        root / "syncer" / "syncer_summary.json",
        root / "learner-0" / "learner-0.checkpoint.json",
        root / "learner-0" / "learner-0.log",
        root / "learner-1" / "learner-1.checkpoint.json",
        root / "learner-1" / "learner-1.log",
    ]
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    artifact_hashes = {
        str(path.relative_to(root)): _sha256_file(path) for path in required if path.exists()
    }
    secret_findings = _scan_for_secrets(root)
    layout = _read_json(root / "layout.json") if (root / "layout.json").exists() else {}
    termination = (
        _read_json(root / "termination_safety.json")
        if (root / "termination_safety.json").exists()
        else {}
    )
    summary = (
        _read_json(root / "syncer" / "syncer_summary.json")
        if (root / "syncer" / "syncer_summary.json").exists()
        else {}
    )
    checkpoint = (
        _read_json(root / "syncer" / "syncer_checkpoint.json")
        if (root / "syncer" / "syncer_checkpoint.json").exists()
        else {}
    )
    events = (
        _read_jsonl(root / "syncer" / "events.jsonl")
        if (root / "syncer" / "events.jsonl").exists()
        else []
    )
    roles = layout.get("roles", {}) if isinstance(layout.get("roles"), dict) else {}
    role_names = sorted(roles)
    instance_ids = [str(value.get("instance_id")) for value in roles.values() if value]
    distinct_role_instances = len(instance_ids) == len(set(instance_ids)) and len(instance_ids) >= 3
    learner_artifacts = _learner_artifacts_present(root)
    nesterov_check = _derive_nesterov_check(events, checkpoint)
    metrics = summary.get("metrics", {}) if isinstance(summary.get("metrics"), dict) else {}
    blockers = _build_blockers(
        missing=missing,
        secret_findings=secret_findings,
        role_names=role_names,
        distinct_role_instances=distinct_role_instances,
        termination=termination,
        metrics=metrics,
        summary=summary,
        nesterov_check=nesterov_check,
        learner_artifacts=learner_artifacts,
    )
    evidence_complete = not blockers and not missing
    return LambdaL2RemoteRuntimeEvidencePackage(
        evidence_complete=evidence_complete,
        lambda_l2_remote_runtime_passed=evidence_complete,
        run_id=_as_optional_str(layout.get("run_id") or summary.get("run_id")),
        remote_instance_count=_as_int(layout.get("remote_instance_count") or len(instance_ids)),
        remote_process_roles=role_names,
        distinct_role_instances=distinct_role_instances,
        network_path=_as_optional_str(layout.get("network_path")),
        committed_sync_rounds=_as_int(metrics.get("committed_sync_rounds")),
        final_global_version=_as_int(summary.get("final_global_version")),
        accepted_updates=_as_int(metrics.get("accepted_updates")),
        useful_tokens_accepted=_as_int(metrics.get("useful_tokens_accepted")),
        inner_optimizer_semantics=_as_optional_str(metrics.get("inner_optimizer_semantics")),
        outer_optimizer_semantics=_as_optional_str(metrics.get("outer_optimizer_semantics")),
        pseudo_gradient_numeric_check_passed=nesterov_check["passed"],
        pseudo_gradient_numeric_rounds_checked=nesterov_check["rounds_checked"],
        independent_nesterov_max_abs_error=nesterov_check["max_abs_error"],
        checkpoint_outer_optimizer_step=nesterov_check["checkpoint_step"],
        checkpoint_velocity_max_abs_error=nesterov_check["checkpoint_velocity_max_abs_error"],
        learner_artifacts_present=learner_artifacts,
        final_instance_count=_as_optional_int(termination.get("observed_final_live_instance_count")),
        artifact_hashes=artifact_hashes,
        missing_items=missing,
        secret_scan_passed=not secret_findings,
        secret_scan_findings=secret_findings,
        blockers=blockers,
        warnings=[
            "Lambda L2 proof uses real billable Lambda instances historically; parser is offline.",
            "L2 proves remote process/instance split, not production scale or Pathway readiness.",
        ],
    )


def load_lambda_l2_remote_runtime_evidence_package(
    path: str | Path,
) -> LambdaL2RemoteRuntimeEvidencePackage:
    return LambdaL2RemoteRuntimeEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_l2_remote_runtime_evidence_package(
    path: str | Path,
    package: LambdaL2RemoteRuntimeEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.to_json(), encoding="utf-8")


def _build_blockers(
    *,
    missing: list[str],
    secret_findings: list[str],
    role_names: list[str],
    distinct_role_instances: bool,
    termination: dict[str, Any],
    metrics: dict[str, Any],
    summary: dict[str, Any],
    nesterov_check: dict[str, Any],
    learner_artifacts: list[str],
) -> list[str]:
    blockers = [f"missing_evidence:{item}" for item in missing]
    if secret_findings:
        blockers.append("secret_scan_failed")
    if role_names != ["learner-0", "learner-1", "syncer"]:
        blockers.append("expected_remote_roles_missing")
    if not distinct_role_instances:
        blockers.append("roles_not_on_distinct_instances")
    if _as_int(metrics.get("committed_sync_rounds")) < 1:
        blockers.append("no_committed_sync_rounds")
    if summary.get("final_global_version") != metrics.get("committed_sync_rounds"):
        blockers.append("final_version_round_count_mismatch")
    if metrics.get("inner_optimizer_semantics") != "adamw":
        blockers.append("inner_optimizer_not_adamw")
    if metrics.get("outer_optimizer_semantics") != "nesterov":
        blockers.append("outer_optimizer_not_nesterov")
    if metrics.get("nesterov_outer_optimizer_exercised") is not True:
        blockers.append("nesterov_not_exercised")
    if not nesterov_check["passed"]:
        blockers.append("pseudo_gradient_numeric_check_failed")
    if sorted(learner_artifacts) != ["learner-0", "learner-1"]:
        blockers.append("expected_two_learner_artifacts_missing")
    if termination.get("observed_final_live_instance_count") != 0:
        blockers.append("final_live_instance_count_not_zero")
    return sorted(set(blockers))


def _derive_nesterov_check(
    events: list[dict[str, Any]],
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    commits = [
        event["payload"]
        for event in events
        if event.get("event_type") == "sync_round_committed"
    ]
    commits.sort(key=lambda payload: _as_int(payload.get("new_global_version")))
    if not commits:
        return _failed_check("no_committed_rounds", rounds_checked=0)
    first = commits[0]
    outer_lr = float(first.get("outer_lr", 0.0))
    momentum = float(first.get("outer_momentum", 0.0))
    velocity = [0.0 for _ in first.get("old_global_vector", [])]
    running_global = [float(value) for value in first.get("old_global_vector", [])]
    max_abs_error = 0.0
    chain_ok = True
    version_ok = True
    previous_version = _as_int(first.get("previous_global_version"))
    for payload in commits:
        old_global = [float(value) for value in payload.get("old_global_vector", [])]
        weighted_delta = [float(value) for value in payload.get("weighted_delta", [])]
        logged_new = [float(value) for value in payload.get("new_global_vector", [])]
        if len(old_global) != len(weighted_delta) or len(old_global) != len(logged_new):
            return _failed_check("vector_shape_mismatch", rounds_checked=len(commits))
        chain_ok = chain_ok and _max_abs_diff(old_global, running_global) <= _NUMERIC_TOLERANCE
        new_global, velocity = _apply_nesterov(
            old_global,
            weighted_delta,
            velocity,
            outer_lr,
            momentum,
        )
        max_abs_error = max(max_abs_error, _max_abs_diff(new_global, logged_new))
        expected_version = previous_version + 1
        version_ok = version_ok and _as_int(payload.get("new_global_version")) == expected_version
        previous_version = expected_version
        running_global = logged_new
    optimizer_state = checkpoint.get("outer_optimizer_state", {})
    checkpoint_velocity = [float(value) for value in optimizer_state.get("velocity", [])]
    checkpoint_velocity_error = _max_abs_diff(checkpoint_velocity, velocity)
    checkpoint_step = _as_optional_int(optimizer_state.get("step"))
    checkpoint_ok = (
        checkpoint_step == len(commits)
        and checkpoint_velocity_error <= _NUMERIC_TOLERANCE
        and optimizer_state.get("outer_optimizer") == "nesterov"
    )
    passed = chain_ok and version_ok and max_abs_error <= _NUMERIC_TOLERANCE and checkpoint_ok
    return {
        "passed": passed,
        "rounds_checked": len(commits),
        "max_abs_error": max_abs_error,
        "checkpoint_step": checkpoint_step,
        "checkpoint_velocity_max_abs_error": checkpoint_velocity_error,
        "reason": None if passed else "nesterov_replay_or_checkpoint_mismatch",
    }


def _failed_check(reason: str, *, rounds_checked: int) -> dict[str, Any]:
    return {
        "passed": False,
        "rounds_checked": rounds_checked,
        "max_abs_error": None,
        "checkpoint_step": None,
        "checkpoint_velocity_max_abs_error": None,
        "reason": reason,
    }


def _apply_nesterov(
    global_vector: list[float],
    weighted_delta: list[float],
    velocity: list[float],
    outer_lr: float,
    momentum: float,
) -> tuple[list[float], list[float]]:
    next_velocity: list[float] = []
    next_global: list[float] = []
    for base, delta, current_velocity in zip(global_vector, weighted_delta, velocity, strict=True):
        pseudo_gradient = -delta
        updated_velocity = momentum * current_velocity + pseudo_gradient
        nesterov_direction = pseudo_gradient + momentum * updated_velocity
        next_velocity.append(updated_velocity)
        next_global.append(base - outer_lr * nesterov_direction)
    return next_global, next_velocity


def _learner_artifacts_present(root: Path) -> list[str]:
    learners: list[str] = []
    for learner_id in ("learner-0", "learner-1"):
        checkpoint_exists = (root / learner_id / f"{learner_id}.checkpoint.json").exists()
        log_exists = (root / learner_id / f"{learner_id}.log").exists()
        if checkpoint_exists and log_exists:
            learners.append(learner_id)
    return learners


def _scan_for_secrets(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for needle in _SECRET_NEEDLES:
            if needle in text:
                findings.append(str(path.relative_to(root)))
                break
    return findings


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _max_abs_diff(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return float("inf")
    if not left:
        return 0.0
    return max(abs(a - b) for a, b in zip(left, right, strict=True))


def _as_int(value: object) -> int:
    if value is None:
        return 0
    return int(value)


def _as_optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    return str(value)
