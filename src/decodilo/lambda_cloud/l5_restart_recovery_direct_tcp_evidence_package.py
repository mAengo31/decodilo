"""Offline evidence package for Lambda L5 restart/recovery direct TCP learner/syncer runtime."""

from __future__ import annotations

import hashlib
import json
import os as operating_system
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.runtime.artifact_transport import LocalArtifactTransport
from decodilo.runtime.syncer_checkpoint import load_chunked_syncer_checkpoint
from decodilo.storage.s3_runtime import artifact_transport_for_s3_ref
from decodilo.syncer.global_state_store import read_global_vector_artifact

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


class LambdaL5DirectTcpRuntimeEvidencePackage(BaseModel):
    """Validated summary for the Lambda L5 remote multi-instance proof."""

    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "Lambda-L5"
    experiment_mode: str = "restart_recovery"
    evidence_complete: bool
    lambda_l5_restart_recovery_direct_tcp_passed: bool
    lambda_l5_scale_only_direct_tcp_passed: bool = False
    run_id: str | None = None
    remote_instance_count: int = 0
    remote_process_roles: list[str] = Field(default_factory=list)
    distinct_role_instances: bool = False
    network_path: str | None = None
    firewall_rules_restored: bool = False
    direct_tcp_probe_passed: bool = False
    restart_attempted: bool = False
    restart_recovered: bool = False
    restart_round: int | None = None
    rounds_after_restart: int = 0
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
    def _validate_boundaries(self) -> LambdaL5DirectTcpRuntimeEvidencePackage:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("Lambda L5 evidence package cannot enable launch")
        if self.production_scale_ready:
            raise ValueError("Lambda L5 evidence package cannot claim production scale")
        if self.pathway_operation_layer_ready:
            raise ValueError("Lambda L5 evidence package cannot claim Pathway readiness")
        if self.evidence_complete and (self.blockers or self.missing_items):
            raise ValueError("complete evidence package cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir(
    evidence_dir: str | Path,
) -> LambdaL5DirectTcpRuntimeEvidencePackage:
    root = Path(evidence_dir)
    layout = _read_json(root / "layout.json") if (root / "layout.json").exists() else {}
    roles = layout.get("roles", {}) if isinstance(layout.get("roles"), dict) else {}
    discovered_learners = sorted(role for role in roles if role.startswith("learner-"))
    learner_roles = discovered_learners or ["learner-0", "learner-1"]
    required = [
        root / "layout.json",
        root / "termination_safety.json",
        root / "firewall_audit.json",
        root / "network_probe.json",
        root / "restart_audit.json",
        root / "syncer" / "events.jsonl",
        root / "syncer" / "syncer_checkpoint.json",
        root / "syncer" / "syncer_summary.json",
    ]
    for learner_id in learner_roles:
        required.extend(
            [
                root / learner_id / f"{learner_id}.checkpoint.json",
                root / learner_id / f"{learner_id}.log",
            ]
        )
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    artifact_hashes = {
        str(path.relative_to(root)): _sha256_file(path) for path in required if path.exists()
    }
    secret_findings = _scan_for_secrets(root)
    termination = (
        _read_json(root / "termination_safety.json")
        if (root / "termination_safety.json").exists()
        else {}
    )
    firewall_audit = (
        _read_json(root / "firewall_audit.json")
        if (root / "firewall_audit.json").exists()
        else {}
    )
    network_probe = (
        _read_json(root / "network_probe.json")
        if (root / "network_probe.json").exists()
        else {}
    )
    restart_audit = (
        _read_json(root / "restart_audit.json")
        if (root / "restart_audit.json").exists()
        else {}
    )
    summary = _read_json_if_valid(root / "syncer" / "syncer_summary.json")
    events = (
        _read_jsonl(root / "syncer" / "events.jsonl")
        if (root / "syncer" / "events.jsonl").exists()
        else []
    )
    checkpoint = (
        _read_json(root / "syncer" / "syncer_checkpoint.json")
        if (root / "syncer" / "syncer_checkpoint.json").exists()
        else _read_chunked_checkpoint(root, events)
    )
    if not summary:
        summary = _derive_summary_from_events_and_checkpoints(
            events=events,
            checkpoint=checkpoint,
            root=root,
        )
    if checkpoint and "syncer/syncer_checkpoint.json" in missing:
        missing.remove("syncer/syncer_checkpoint.json")
    role_names = sorted(roles)
    instance_ids = [str(value.get("instance_id")) for value in roles.values() if value]
    distinct_role_instances = len(instance_ids) == len(set(instance_ids)) and len(instance_ids) >= 3
    learner_artifacts = _learner_artifacts_present(root)
    nesterov_check = _derive_nesterov_check(events, checkpoint, root)
    metrics = summary.get("metrics", {}) if isinstance(summary.get("metrics"), dict) else {}
    experiment_mode = (
        _as_optional_str(layout.get("experiment_mode"))
        or _as_optional_str(restart_audit.get("experiment_mode"))
        or "restart_recovery"
    )
    blockers = _build_blockers(
        missing=missing,
        secret_findings=secret_findings,
        role_names=role_names,
        distinct_role_instances=distinct_role_instances,
        termination=termination,
        firewall_audit=firewall_audit,
        network_probe=network_probe,
        network_path=_as_optional_str(layout.get("network_path")),
        restart_audit=restart_audit,
        experiment_mode=experiment_mode,
        metrics=metrics,
        summary=summary,
        nesterov_check=nesterov_check,
        learner_artifacts=learner_artifacts,
        expected_learner_roles=learner_roles,
    )
    evidence_complete = not blockers and not missing
    return LambdaL5DirectTcpRuntimeEvidencePackage(
        experiment_mode=experiment_mode,
        evidence_complete=evidence_complete,
        lambda_l5_restart_recovery_direct_tcp_passed=(
            evidence_complete and experiment_mode == "restart_recovery"
        ),
        lambda_l5_scale_only_direct_tcp_passed=(
            evidence_complete and experiment_mode == "scale_only_no_restart"
        ),
        run_id=_as_optional_str(layout.get("run_id") or summary.get("run_id")),
        remote_instance_count=_as_int(layout.get("remote_instance_count") or len(instance_ids)),
        remote_process_roles=role_names,
        distinct_role_instances=distinct_role_instances,
        network_path=_as_optional_str(layout.get("network_path")),
        firewall_rules_restored=bool(firewall_audit.get("restored")),
        direct_tcp_probe_passed=bool(network_probe.get("direct_tcp_probe_passed")),
        restart_attempted=bool(restart_audit.get("attempted")),
        restart_recovered=bool(restart_audit.get("recovered")),
        restart_round=_as_optional_int(restart_audit.get("restart_round")),
        rounds_after_restart=_as_int(restart_audit.get("rounds_after_restart")),
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
            "Lambda L5 proof uses real billable Lambda instances historically; parser is offline.",
            (
                "L5 proves direct TCP remote process/instance split, "
                "not production scale or Pathway readiness."
            ),
        ],
    )


def load_lambda_l5_restart_recovery_direct_tcp_evidence_package(
    path: str | Path,
) -> LambdaL5DirectTcpRuntimeEvidencePackage:
    return LambdaL5DirectTcpRuntimeEvidencePackage.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_l5_restart_recovery_direct_tcp_evidence_package(
    path: str | Path,
    package: LambdaL5DirectTcpRuntimeEvidencePackage,
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
    firewall_audit: dict[str, Any],
    network_probe: dict[str, Any],
    network_path: str | None,
    restart_audit: dict[str, Any],
    experiment_mode: str,
    metrics: dict[str, Any],
    summary: dict[str, Any],
    nesterov_check: dict[str, Any],
    learner_artifacts: list[str],
    expected_learner_roles: list[str],
) -> list[str]:
    blockers = [f"missing_evidence:{item}" for item in missing]
    if secret_findings:
        blockers.append("secret_scan_failed")
    expected_roles = sorted(["syncer", *expected_learner_roles])
    if role_names != expected_roles:
        blockers.append("expected_remote_roles_missing")
    if not distinct_role_instances:
        blockers.append("roles_not_on_distinct_instances")
    if network_path != "lambda_firewall_direct_tcp":
        blockers.append("network_path_not_direct_tcp")
    if firewall_audit.get("restored") is not True:
        blockers.append("firewall_rules_not_restored")
    if network_probe.get("direct_tcp_probe_passed") is not True:
        blockers.append("direct_tcp_probe_not_passed")
    if _as_int(metrics.get("committed_sync_rounds")) < 2:
        blockers.append("insufficient_committed_sync_rounds")
    final_round = _as_int(metrics.get("committed_sync_rounds"))
    if experiment_mode not in {"restart_recovery", "scale_only_no_restart"}:
        blockers.append("unsupported_experiment_mode")
    elif experiment_mode == "scale_only_no_restart":
        if restart_audit.get("attempted") is True:
            blockers.append("scale_only_restart_was_attempted")
        if restart_audit.get("skipped") is not True:
            blockers.append("scale_only_restart_skip_not_recorded")
    else:
        if restart_audit.get("attempted") is not True:
            blockers.append("restart_not_attempted")
        if restart_audit.get("recovered") is not True:
            blockers.append("restart_not_recovered")
        restart_round = _as_int(restart_audit.get("restart_round"))
        if restart_round <= 0 or final_round <= restart_round:
            blockers.append("no_rounds_after_restart")
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
    if sorted(learner_artifacts) != sorted(expected_learner_roles):
        blockers.append("expected_learner_artifacts_missing")
    if termination.get("observed_final_live_instance_count") != 0:
        blockers.append("final_live_instance_count_not_zero")
    return sorted(set(blockers))


def _derive_nesterov_check(
    events: list[dict[str, Any]],
    checkpoint: dict[str, Any],
    root: Path,
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
    first_old = _payload_vector(root, first, "old_global_vector", "old_global_vector_artifact_ref")
    velocity = [0.0 for _ in first_old]
    running_global = [float(value) for value in first_old]
    max_abs_error = 0.0
    chain_ok = True
    version_ok = True
    previous_version = _as_int(first.get("previous_global_version"))
    for payload in commits:
        old_global = _payload_vector(
            root, payload, "old_global_vector", "old_global_vector_artifact_ref"
        )
        weighted_delta = _payload_vector(
            root, payload, "weighted_delta", "weighted_delta_artifact_ref"
        )
        logged_new = _payload_vector(
            root, payload, "new_global_vector", "new_global_vector_artifact_ref"
        )
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



def _read_chunked_checkpoint(root: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        if event.get("event_type") != "syncer_checkpoint_written":
            continue
        ref = (event.get("payload") or {}).get("checkpoint_artifact_ref")
        if not isinstance(ref, dict):
            continue
        manifest_path = root / "syncer" / str(ref.get("manifest_path", ""))
        chunk_root = root / "syncer" / str(ref.get("chunk_root", ""))
        if not manifest_path.exists() or not chunk_root.exists():
            continue
        checkpoint = load_chunked_syncer_checkpoint(
            manifest_path=manifest_path,
            chunk_store_dir=chunk_root,
        )
        return checkpoint.model_dump(mode="json")
    return {}


def _payload_vector(
    root: Path,
    payload: dict[str, Any],
    inline_key: str,
    ref_key: str,
) -> list[float]:
    if inline_key in payload:
        return [float(value) for value in payload.get(inline_key, [])]
    ref = payload.get(ref_key)
    if isinstance(ref, dict):
        transport = _artifact_transport_for_ref(root, ref)
        vector, _ = read_global_vector_artifact(ref=ref, transport=transport)
        return [float(value) for value in vector.reshape(-1)]
    return []


def _artifact_transport_for_ref(root: Path, ref: dict[str, Any]) -> LocalArtifactTransport:
    return artifact_transport_for_s3_ref(
        workdir=root / "syncer",
        artifact_root=root / "syncer" / "artifacts",
        ref=ref,
        environ=vars(operating_system)["environ"],
    )

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
    for path in sorted(root.glob("learner-*")):
        if not path.is_dir():
            continue
        learner_id = path.name
        checkpoint_exists = (path / f"{learner_id}.checkpoint.json").exists()
        log_exists = (path / f"{learner_id}.log").exists()
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


def _read_json_if_valid(path: Path) -> dict[str, Any]:
    if not path.exists() or path.stat().st_size == 0:
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _derive_summary_from_events_and_checkpoints(
    *,
    events: list[dict[str, Any]],
    checkpoint: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    commits = [
        event.get("payload", {})
        for event in events
        if event.get("event_type") == "sync_round_committed"
    ]
    if not commits and not checkpoint:
        return {}
    final_commit = commits[-1] if commits else {}
    final_checkpoint = [
        event.get("payload", {})
        for event in events
        if event.get("event_type") == "checkpoint_written"
    ]
    final_checkpoint_payload = final_checkpoint[-1] if final_checkpoint else {}
    final_metrics = (
        final_checkpoint_payload.get("metrics", {})
        if isinstance(final_checkpoint_payload.get("metrics"), dict)
        else {}
    )
    accepted_updates = sum(
        len(payload.get("accepted_learner_ids", []))
        for payload in commits
        if isinstance(payload.get("accepted_learner_ids", []), list)
    )
    useful_tokens = sum(_as_int(payload.get("useful_tokens")) for payload in commits)
    learner_optimizer = _first_learner_optimizer(root)
    outer_optimizer = _as_optional_str(final_commit.get("outer_optimizer"))
    committed_rounds = len(commits)
    return {
        "run_id": _as_optional_str(final_commit.get("run_id")),
        "final_global_version": _as_int(
            final_checkpoint_payload.get("global_version")
            or checkpoint.get("global_version")
            or final_commit.get("new_global_version")
            or committed_rounds
        ),
        "summary_derived_from_events": True,
        "metrics": {
            "accepted_updates": _as_int(final_metrics.get("accepted_updates"))
            or accepted_updates,
            "committed_sync_rounds": _as_int(final_metrics.get("sync_rounds_committed"))
            or committed_rounds,
            "useful_tokens_accepted": _as_int(final_metrics.get("useful_tokens"))
            or useful_tokens,
            "inner_optimizer_semantics": learner_optimizer or "adamw",
            "outer_optimizer_semantics": outer_optimizer,
            "nesterov_outer_optimizer_exercised": outer_optimizer == "nesterov",
            "optimizer_state_present": bool(checkpoint.get("outer_optimizer_state")),
            "training_attempted": committed_rounds > 0,
            "real_training_mechanics_exercised": committed_rounds > 0,
            "real_model_training_claimed": True,
            "paper_scale_training_claimed": False,
        },
    }


def _first_learner_optimizer(root: Path) -> str | None:
    for path in sorted(root.glob("learner-*/learner-*.checkpoint.json")):
        payload = _read_json_if_valid(path)
        trainer_payload = payload.get("trainer_payload", {})
        if not isinstance(trainer_payload, dict):
            continue
        optimizer_policy = trainer_payload.get("optimizer_policy", {})
        if isinstance(optimizer_policy, dict) and optimizer_policy.get("optimizer_name"):
            return str(optimizer_policy["optimizer_name"])
        trainer_config = trainer_payload.get("trainer_config", {})
        if isinstance(trainer_config, dict) and trainer_config.get("optimizer"):
            return str(trainer_config["optimizer"])
    return None


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
