"""Provider-neutral conformance suite for future remote artifact backends.

The suite runs only against local simulator objects or disabled backends. It is
evidence for future review, not a real remote backend implementation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.disabled_remote_backend import (
    DisabledRemoteArtifactBackend,
    RemoteBackendDisabledError,
)
from decodilo.storage.remote_backend_conformance_cases import (
    RemoteBackendConformanceCase,
    default_conformance_cases,
)
from decodilo.storage.remote_backend_consistency import RemoteBackendConsistencyConfig
from decodilo.storage.remote_backend_faults import RemoteBackendFaultConfig
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet
from decodilo.storage.remote_backend_simulator import (
    LocalRemoteBackendSimulator,
    RemoteBackendSimulatorConfig,
)

REQUIRED_SYMBOLIC_SCOPES = {
    "syncer_manifest_read_write",
    "learner_fragment_write",
    "learner_global_update_read",
    "replay_artifact_read",
    "gc_delete",
}


class RemoteBackendConformanceSuite(BaseModel):
    model_config = ConfigDict(frozen=True)

    suite_schema_version: int = 1
    cases: list[RemoteBackendConformanceCase] = Field(default_factory=default_conformance_cases)


class RemoteBackendConformanceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    category: str
    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


class RemoteBackendConformanceReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    scenario_id: str
    backend_profile: str
    simulator_only: bool = True
    disabled_backend: bool = False
    conformance_status: str
    passed: bool
    cases_run: int
    cases_passed: int
    cases_failed: int
    results: list[RemoteBackendConformanceResult]
    failed_cases: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def passing_simulator_config(
    requirements: RemoteBackendRequirementSet,
) -> RemoteBackendSimulatorConfig:
    return RemoteBackendSimulatorConfig(
        read_gbps=max(1.0, requirements.peak_artifact_read_gbps * 1.25),
        write_gbps=max(1.0, requirements.peak_artifact_write_gbps * 1.25),
        ops_per_second=max(100.0, requirements.peak_artifact_ops_per_second * 2),
        conditional_put=True,
        atomic_manifest_commit=True,
        content_hash_validation=True,
        idempotent_put=True,
        idempotent_delete=True,
        lifecycle_delete=True,
        consistency=RemoteBackendConsistencyConfig(
            strong_read_after_write=True,
            monotonic_manifest_visibility=True,
            object_versioning=True,
        ),
    )


def run_remote_backend_conformance_suite(
    *,
    requirements: RemoteBackendRequirementSet,
    simulator_config: RemoteBackendSimulatorConfig,
    backend_profile: str = "local_simulator",
) -> RemoteBackendConformanceReport:
    suite = RemoteBackendConformanceSuite()
    results: list[RemoteBackendConformanceResult] = []
    for case in suite.cases:
        runner = _CASE_RUNNERS[case.case_id]
        results.append(runner(requirements, simulator_config))
    failed = [result.case_id for result in results if not result.passed]
    warnings = [
        "simulator conformance is not production backend readiness",
        "no real remote backend is enabled",
    ]
    return RemoteBackendConformanceReport(
        scenario_id=requirements.scenario_id,
        backend_profile=backend_profile,
        conformance_status="passed" if not failed else "failed",
        passed=not failed,
        cases_run=len(results),
        cases_passed=len(results) - len(failed),
        cases_failed=len(failed),
        results=results,
        failed_cases=failed,
        warnings=warnings,
    )


def run_disabled_backend_conformance() -> RemoteBackendConformanceReport:
    backend = DisabledRemoteArtifactBackend()
    result: RemoteBackendConformanceResult
    try:
        backend.write_bytes(artifact_id="probe", data=b"")
    except RemoteBackendDisabledError:
        result = RemoteBackendConformanceResult(
            case_id="disabled_backend_rejects_operations",
            category="disabled",
            passed=True,
            evidence={"disabled": True},
        )
    else:
        result = RemoteBackendConformanceResult(
            case_id="disabled_backend_rejects_operations",
            category="disabled",
            passed=False,
            errors=["disabled backend unexpectedly allowed an operation"],
        )
    return RemoteBackendConformanceReport(
        scenario_id="disabled-backend",
        backend_profile="disabled_remote_backend",
        simulator_only=False,
        disabled_backend=True,
        conformance_status="disabled",
        passed=False,
        cases_run=1,
        cases_passed=1 if result.passed else 0,
        cases_failed=0 if result.passed else 1,
        results=[result],
        failed_cases=[] if result.passed else [result.case_id],
        warnings=["disabled backend is intentionally unusable"],
    )


def load_remote_backend_conformance_report(path: str | Path) -> RemoteBackendConformanceReport:
    return RemoteBackendConformanceReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_remote_backend_conformance_report(
    path: str | Path,
    report: RemoteBackendConformanceReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _basic_artifact_operations(
    _requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    sim = LocalRemoteBackendSimulator(config)
    errors: list[str] = []
    try:
        put = sim.put_artifact("basic", b"abcdef")
        if sim.get_artifact("basic") != b"abcdef":
            errors.append("get returned wrong bytes")
        if sim.get_range("basic", 1, 3) != b"bcd":
            errors.append("range read returned wrong bytes")
        if "basic" not in sim.list_artifacts():
            errors.append("list did not include visible object")
        sim.delete_artifact("basic")
        try:
            sim.get_artifact("basic")
        except KeyError:
            pass
        else:
            errors.append("deleted object remained visible")
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
        put = {}
    return RemoteBackendConformanceResult(
        case_id="basic_artifact_operations",
        category="basic",
        passed=not errors,
        errors=errors,
        evidence={"version": put.get("version"), "metrics": sim.metrics.model_dump(mode="json")},
    )


def _integrity_corrupt_read_detected(
    _requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    if not config.content_hash_validation:
        return _failed(
            "integrity_corrupt_read_detected",
            "integrity",
            "content hash validation disabled",
        )
    faulted = config.model_copy(update={"faults": RemoteBackendFaultConfig(corrupt_read_after=1)})
    sim = LocalRemoteBackendSimulator(faulted)
    try:
        sim.put_artifact("integrity", b"payload")
        sim.get_artifact("integrity")
    except ValueError as exc:
        return RemoteBackendConformanceResult(
            case_id="integrity_corrupt_read_detected",
            category="integrity",
            passed=True,
            evidence={
                "error": str(exc),
                "corruptions_detected": sim.metrics.simulated_corruptions_detected,
            },
        )
    except Exception as exc:  # noqa: BLE001
        return _failed("integrity_corrupt_read_detected", "integrity", str(exc))
    return _failed("integrity_corrupt_read_detected", "integrity", "corrupt read was not detected")


def _consistency_read_after_write(
    requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    errors: list[str] = []
    if requirements.required_read_after_write_consistency and not (
        config.consistency.strong_read_after_write
    ):
        errors.append("read-after-write consistency is required but not declared")
    if requirements.required_monotonic_manifest_visibility and not (
        config.consistency.monotonic_manifest_visibility
    ):
        errors.append("monotonic manifest visibility is required but not declared")
    return RemoteBackendConformanceResult(
        case_id="consistency_read_after_write",
        category="consistency",
        passed=not errors,
        errors=errors,
        evidence=config.consistency.model_dump(mode="json"),
    )


def _conditional_put_conflict(
    requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    if requirements.required_conditional_put and not config.conditional_put:
        return _failed("conditional_put_conflict", "consistency", "conditional put disabled")
    sim = LocalRemoteBackendSimulator(config)
    try:
        put = sim.put_artifact("conditional", b"one")
        sim.put_artifact("conditional", b"two", expected_version=int(put["version"]) + 1)
    except ValueError:
        return RemoteBackendConformanceResult(
            case_id="conditional_put_conflict",
            category="consistency",
            passed=True,
            evidence={"conflict_rejected": True},
        )
    except Exception as exc:  # noqa: BLE001
        return _failed("conditional_put_conflict", "consistency", str(exc))
    return _failed("conditional_put_conflict", "consistency", "conditional conflict was accepted")


def _retry_and_idempotency(
    _requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    if not (config.idempotent_put and config.idempotent_delete):
        return _failed("retry_and_idempotency", "retry_idempotency", "idempotency disabled")
    retry_config = config.model_copy(
        update={
            "faults": RemoteBackendFaultConfig(
                transient_put_failures=1,
                transient_get_failures=1,
            )
        }
    )
    sim = LocalRemoteBackendSimulator(retry_config)
    errors: list[str] = []
    try:
        try:
            sim.put_artifact("retry", b"payload")
        except RuntimeError:
            pass
        first = sim.put_artifact("retry", b"payload")
        duplicate = sim.put_artifact("retry", b"payload")
        if first["version"] != duplicate["version"]:
            errors.append("duplicate put changed version")
        try:
            sim.get_artifact("retry")
        except RuntimeError:
            pass
        if sim.get_artifact("retry") != b"payload":
            errors.append("retry get returned wrong bytes")
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
    return RemoteBackendConformanceResult(
        case_id="retry_and_idempotency",
        category="retry_idempotency",
        passed=not errors,
        errors=errors,
        evidence={"retries": sim.metrics.simulated_retries},
    )


def _partial_write_not_visible(
    _requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    faulted = config.model_copy(
        update={"faults": RemoteBackendFaultConfig(partial_write_failure=True)}
    )
    sim = LocalRemoteBackendSimulator(faulted)
    try:
        sim.put_artifact("partial", b"payload")
    except RuntimeError:
        visible = "partial" in sim.list_artifacts()
        return RemoteBackendConformanceResult(
            case_id="partial_write_not_visible",
            category="retry_idempotency",
            passed=not visible,
            errors=[] if not visible else ["partial write became visible"],
            evidence={"visible_after_failure": visible},
        )
    return _failed("partial_write_not_visible", "retry_idempotency", "partial write did not fail")


def _lifecycle_delete_transaction(
    requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    errors: list[str] = []
    if requirements.required_lifecycle_delete and not config.lifecycle_delete:
        errors.append("lifecycle delete disabled")
    if requirements.required_transaction_log and not config.idempotent_delete:
        errors.append("delete transaction/idempotency support missing")
    return RemoteBackendConformanceResult(
        case_id="lifecycle_delete_transaction",
        category="lifecycle_gc",
        passed=not errors,
        errors=errors,
        evidence={
            "lifecycle_delete": config.lifecycle_delete,
            "idempotent_delete": config.idempotent_delete,
        },
    )


def _replay_checkpoint_restore(
    _requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    sim = LocalRemoteBackendSimulator(config)
    data = b"checkpoint-snapshot-event-segment"
    digest = hashlib.sha256(data).hexdigest()
    errors: list[str] = []
    try:
        sim.put_artifact("restore", data)
        restored = sim.get_range("restore", 0, len(data))
        if hashlib.sha256(restored).hexdigest() != digest:
            errors.append("range-read restore checksum mismatch")
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))
    return RemoteBackendConformanceResult(
        case_id="replay_checkpoint_restore",
        category="replay_restore",
        passed=not errors,
        errors=errors,
        evidence={"sha256": digest, "range_gets": sim.metrics.simulated_range_gets},
    )


def _security_symbolic_scopes(
    _requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    scopes = set(getattr(config, "auth_scopes", []))
    missing = sorted(REQUIRED_SYMBOLIC_SCOPES - scopes)
    errors = [f"missing symbolic auth scopes: {missing}"] if missing else []
    return RemoteBackendConformanceResult(
        case_id="security_symbolic_scopes",
        category="security",
        passed=not errors,
        errors=errors,
        evidence={"scope_count": len(scopes), "missing": missing},
    )


def _bandwidth_and_cost_accounting(
    requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendConformanceResult:
    errors: list[str] = []
    if config.read_gbps < requirements.peak_artifact_read_gbps:
        errors.append("read bandwidth below requirement")
    if config.write_gbps < requirements.peak_artifact_write_gbps:
        errors.append("write bandwidth below requirement")
    if config.ops_per_second < requirements.peak_artifact_ops_per_second:
        errors.append("ops/sec below requirement")
    return RemoteBackendConformanceResult(
        case_id="bandwidth_and_cost_accounting",
        category="bandwidth_cost",
        passed=not errors,
        errors=errors,
        evidence={
            "read_gbps": config.read_gbps,
            "write_gbps": config.write_gbps,
            "ops_per_second": config.ops_per_second,
        },
    )


def _failed(case_id: str, category: str, error: str) -> RemoteBackendConformanceResult:
    return RemoteBackendConformanceResult(
        case_id=case_id,
        category=category,
        passed=False,
        errors=[error],
    )


_CASE_RUNNERS = {
    "basic_artifact_operations": _basic_artifact_operations,
    "integrity_corrupt_read_detected": _integrity_corrupt_read_detected,
    "consistency_read_after_write": _consistency_read_after_write,
    "conditional_put_conflict": _conditional_put_conflict,
    "retry_and_idempotency": _retry_and_idempotency,
    "partial_write_not_visible": _partial_write_not_visible,
    "lifecycle_delete_transaction": _lifecycle_delete_transaction,
    "replay_checkpoint_restore": _replay_checkpoint_restore,
    "security_symbolic_scopes": _security_symbolic_scopes,
    "bandwidth_and_cost_accounting": _bandwidth_and_cost_accounting,
}
