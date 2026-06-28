"""Offline evidence package for the Lambda L1 AdamW/Nesterov runtime proof."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

_NUMERIC_TOLERANCE = 1e-9
_REQUIRED_FILES = (
    "report.json",
    "events.jsonl",
    "syncer_checkpoint.json",
    "learner-0.checkpoint.json",
    "learner-0.log",
    "learner-1.checkpoint.json",
    "learner-1.log",
    "termination_safety.json",
)
_SECRET_NEEDLES = (
    "lambda_api_key=",
    "lambda_ssh_key=",
    "-----begin ",
    "jupyter token",
    "jupyter_token",
    "authorization: bearer",
    "authorization: basic",
)


class LambdaL1RuntimeEvidencePackage(BaseModel):
    """Validated, immutable summary for a single-instance Lambda L1 proof.

    The package records a historical billable verification run, but this parser is offline
    and cannot authorize or launch future Lambda work.
    """

    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "Lambda-L1"
    evidence_complete: bool
    lambda_l1_runtime_passed: bool
    run_id: str | None = None
    instance_id: str | None = None
    region: str | None = None
    instance_type: str | None = None
    final_instance_count: int | None = None
    billable_action_performed: bool = True
    billable_action_scope: str = "historical_single_lambda_instance_verification"
    evidence_package_builder_billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    production_scale_ready: bool = False
    multi_instance_distributed_ready: bool = False
    pathway_operation_layer_ready: bool = False
    trainer_type: str | None = None
    inner_optimizer_semantics: str | None = None
    outer_optimizer_semantics: str | None = None
    committed_sync_rounds: int = 0
    final_global_version: int = 0
    accepted_updates: int = 0
    useful_tokens_accepted: int = 0
    pseudo_gradient_numeric_check_passed: bool = False
    pseudo_gradient_numeric_rounds_checked: int = 0
    independent_nesterov_max_abs_error: float | None = None
    checkpoint_outer_optimizer_step: int | None = None
    checkpoint_velocity_max_abs_error: float | None = None
    replay_passed: bool = False
    metric_validation_passed: bool = False
    learner_artifacts_present: list[str] = Field(default_factory=list)
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    missing_items: list[str] = Field(default_factory=list)
    hash_mismatches: list[str] = Field(default_factory=list)
    secret_scan_passed: bool = False
    secret_scan_findings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_safety_flags(self) -> LambdaL1RuntimeEvidencePackage:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("Lambda L1 evidence package cannot enable launch")
        if self.production_scale_ready or self.multi_instance_distributed_ready:
            raise ValueError(
                "Lambda L1 package cannot claim production or multi-instance readiness"
            )
        if self.pathway_operation_layer_ready:
            raise ValueError("Lambda L1 package cannot claim Pathway/op-layer readiness")
        if self.evidence_complete and (self.blockers or self.missing_items):
            raise ValueError("complete evidence package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_l1_runtime_evidence_package_from_dir(
    evidence_dir: str | Path,
) -> LambdaL1RuntimeEvidencePackage:
    """Build an offline package from copied Lambda L1 runtime artifacts."""

    root = Path(evidence_dir)
    missing = [name for name in _REQUIRED_FILES if not (root / name).exists()]
    artifact_hashes = {
        name: _sha256_file(root / name)
        for name in _REQUIRED_FILES
        if (root / name).exists()
    }
    secret_findings = _scan_for_secrets(root)

    report = _read_json(root / "report.json") if (root / "report.json").exists() else {}
    checkpoint = (
        _read_json(root / "syncer_checkpoint.json")
        if (root / "syncer_checkpoint.json").exists()
        else {}
    )
    termination = (
        _read_json(root / "termination_safety.json")
        if (root / "termination_safety.json").exists()
        else {}
    )
    events = _read_jsonl(root / "events.jsonl") if (root / "events.jsonl").exists() else []
    nesterov_check = _derive_nesterov_check(events, checkpoint)

    metrics = report.get("metrics", {}) if isinstance(report.get("metrics"), dict) else {}
    replay_validation = (
        report.get("replay_validation", {})
        if isinstance(report.get("replay_validation"), dict)
        else {}
    )
    metric_validation = (
        report.get("metric_validation", {})
        if isinstance(report.get("metric_validation"), dict)
        else {}
    )
    learner_artifacts = _learner_artifacts_present(root)

    blockers = _build_blockers(
        missing=missing,
        secret_findings=secret_findings,
        report=report,
        metrics=metrics,
        replay_validation=replay_validation,
        metric_validation=metric_validation,
        termination=termination,
        nesterov_check=nesterov_check,
        learner_artifacts=learner_artifacts,
    )
    evidence_complete = not blockers and not missing

    return LambdaL1RuntimeEvidencePackage(
        evidence_complete=evidence_complete,
        lambda_l1_runtime_passed=evidence_complete,
        run_id=_as_optional_str(report.get("run_id")),
        instance_id=_as_optional_str(termination.get("instance_id")),
        region=_as_optional_str(termination.get("region")),
        instance_type=_as_optional_str(termination.get("instance_type")),
        final_instance_count=_as_optional_int(
            termination.get("observed_final_live_instance_count")
        ),
        trainer_type=_as_optional_str(report.get("trainer_type")),
        inner_optimizer_semantics=_as_optional_str(
            metrics.get("inner_optimizer_semantics")
        ),
        outer_optimizer_semantics=_as_optional_str(
            metrics.get("outer_optimizer_semantics")
        ),
        committed_sync_rounds=_as_int(metrics.get("committed_sync_rounds")),
        final_global_version=_as_int(report.get("final_global_version")),
        accepted_updates=_as_int(metrics.get("accepted_updates")),
        useful_tokens_accepted=_as_int(metrics.get("useful_tokens_accepted")),
        pseudo_gradient_numeric_check_passed=nesterov_check["passed"],
        pseudo_gradient_numeric_rounds_checked=nesterov_check["rounds_checked"],
        independent_nesterov_max_abs_error=nesterov_check["max_abs_error"],
        checkpoint_outer_optimizer_step=nesterov_check["checkpoint_step"],
        checkpoint_velocity_max_abs_error=nesterov_check["checkpoint_velocity_max_abs_error"],
        replay_passed=bool(replay_validation.get("replay_passed")),
        metric_validation_passed=bool(metric_validation.get("passed")),
        learner_artifacts_present=learner_artifacts,
        artifact_hashes=artifact_hashes,
        missing_items=missing,
        secret_scan_passed=not secret_findings,
        secret_scan_findings=secret_findings,
        blockers=blockers,
        warnings=[
            (
                "Lambda L1 proof used one billable Lambda instance historically; "
                "parser performs no live calls."
            ),
            "Evidence proves single-machine local-loopback learner/syncer runtime only.",
            (
                "Evidence does not prove multi-instance distributed Lambda, "
                "production scale, or Pathway readiness."
            ),
        ],
    )


def load_lambda_l1_runtime_evidence_package(
    path: str | Path,
) -> LambdaL1RuntimeEvidencePackage:
    return LambdaL1RuntimeEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_l1_runtime_evidence_package(
    path: str | Path,
    package: LambdaL1RuntimeEvidencePackage,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(package.to_json(), encoding="utf-8")


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
        return {
            "passed": False,
            "rounds_checked": 0,
            "max_abs_error": None,
            "checkpoint_step": None,
            "checkpoint_velocity_max_abs_error": None,
            "reason": "no_committed_rounds",
        }

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
            return {
                "passed": False,
                "rounds_checked": len(commits),
                "max_abs_error": None,
                "checkpoint_step": None,
                "checkpoint_velocity_max_abs_error": None,
                "reason": "vector_shape_mismatch",
            }
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
    )
    passed = (
        chain_ok
        and version_ok
        and max_abs_error <= _NUMERIC_TOLERANCE
        and checkpoint_ok
        and optimizer_state.get("outer_optimizer") == "nesterov"
    )
    return {
        "passed": passed,
        "rounds_checked": len(commits),
        "max_abs_error": max_abs_error,
        "checkpoint_step": checkpoint_step,
        "checkpoint_velocity_max_abs_error": checkpoint_velocity_error,
        "reason": None if passed else "nesterov_replay_or_checkpoint_mismatch",
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


def _build_blockers(
    *,
    missing: list[str],
    secret_findings: list[str],
    report: dict[str, Any],
    metrics: dict[str, Any],
    replay_validation: dict[str, Any],
    metric_validation: dict[str, Any],
    termination: dict[str, Any],
    nesterov_check: dict[str, Any],
    learner_artifacts: list[str],
) -> list[str]:
    blockers: list[str] = []
    blockers.extend(f"missing_evidence:{item}" for item in missing)
    if secret_findings:
        blockers.append("secret_scan_failed")
    if report.get("trainer_type") != "tiny_adamw":
        blockers.append("trainer_not_tiny_adamw")
    if metrics.get("inner_optimizer_semantics") != "adamw":
        blockers.append("inner_optimizer_not_adamw")
    if metrics.get("outer_optimizer_semantics") != "nesterov":
        blockers.append("outer_optimizer_not_nesterov")
    if _as_int(metrics.get("committed_sync_rounds")) < 1:
        blockers.append("no_committed_sync_rounds")
    if _as_int(report.get("final_global_version")) != _as_int(metrics.get("committed_sync_rounds")):
        blockers.append("final_version_round_count_mismatch")
    if metrics.get("pseudo_gradient_numeric_check_passed") is not True:
        blockers.append("report_pseudo_gradient_numeric_check_not_passed")
    if not nesterov_check["passed"]:
        blockers.append("pseudo_gradient_numeric_check_failed")
    if replay_validation.get("replay_passed") is not True:
        blockers.append("replay_not_passed")
    if metric_validation.get("passed") is not True:
        blockers.append("metric_validation_not_passed")
    if report.get("launch_ready") is not False or report.get("launch_allowed") is not False:
        blockers.append("report_launch_flags_not_disabled")
    if report.get("remote_backend_enabled") is not False:
        blockers.append("remote_backend_enabled_in_local_runtime_report")
    if termination.get("observed_final_live_instance_count") != 0:
        blockers.append("final_live_instance_count_not_zero")
    if sorted(learner_artifacts) != ["learner-0", "learner-1"]:
        blockers.append("expected_two_learner_artifacts_missing")
    return sorted(set(blockers))


def _learner_artifacts_present(root: Path) -> list[str]:
    learners: list[str] = []
    for learner_id in ("learner-0", "learner-1"):
        checkpoint_exists = (root / f"{learner_id}.checkpoint.json").exists()
        log_exists = (root / f"{learner_id}.log").exists()
        if checkpoint_exists and log_exists:
            learners.append(learner_id)
    return learners


def _scan_for_secrets(root: Path) -> list[str]:
    findings: list[str] = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        for needle in _SECRET_NEEDLES:
            if needle in text:
                findings.append(path.name)
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
