"""Local remote-backend simulator for design validation.

The simulator stores objects in memory and advances logical time. It does not
open sockets, call cloud APIs, or read credentials.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.remote_backend_consistency import RemoteBackendConsistencyConfig
from decodilo.storage.remote_backend_faults import RemoteBackendFaultConfig, RemoteBackendFaultState
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


class RemoteBackendSimulatorConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    read_gbps: float = Field(gt=0)
    write_gbps: float = Field(gt=0)
    ops_per_second: float = Field(gt=0)
    put_latency_ms: float = Field(default=0.0, ge=0)
    get_latency_ms: float = Field(default=0.0, ge=0)
    list_latency_ms: float = Field(default=0.0, ge=0)
    conditional_put: bool = True
    atomic_manifest_commit: bool = True
    content_hash_validation: bool = True
    idempotent_put: bool = True
    idempotent_delete: bool = True
    lifecycle_delete: bool = True
    auth_scopes: list[str] = Field(
        default_factory=lambda: [
            "learner-artifact-write",
            "syncer-artifact-read",
            "syncer_manifest_read_write",
            "learner_fragment_write",
            "learner_global_update_read",
            "replay_artifact_read",
            "gc_delete",
        ]
    )
    seed: int = 0
    consistency: RemoteBackendConsistencyConfig = Field(
        default_factory=RemoteBackendConsistencyConfig
    )
    faults: RemoteBackendFaultConfig = Field(default_factory=RemoteBackendFaultConfig)


class RemoteBackendSimulatorMetrics(BaseModel):
    model_config = ConfigDict(frozen=False)

    simulated_puts: int = 0
    simulated_gets: int = 0
    simulated_range_gets: int = 0
    simulated_lists: int = 0
    simulated_deletes: int = 0
    simulated_bytes_read: int = 0
    simulated_bytes_written: int = 0
    simulated_read_throttle_events: int = 0
    simulated_write_throttle_events: int = 0
    simulated_consistency_delays: int = 0
    simulated_retries: int = 0
    simulated_corruptions_detected: int = 0
    simulated_cost_estimate: float = 0.0


class RemoteBackendSimulationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    config: dict
    metrics: dict
    throughput_validation: dict[str, bool | float]
    latency_validation: dict[str, bool | float | None]
    consistency_validation: dict[str, bool]
    integrity_validation: dict[str, bool]
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


@dataclass
class _ObjectRecord:
    data: bytes
    sha256: str
    version: int
    visible_at: int
    deleted_at: int | None = None


class LocalRemoteBackendSimulator:
    def __init__(self, config: RemoteBackendSimulatorConfig) -> None:
        self.config = config
        self.metrics = RemoteBackendSimulatorMetrics()
        self._objects: dict[str, _ObjectRecord] = {}
        self._time = 0
        self._fault_state = RemoteBackendFaultState()

    @property
    def logical_time(self) -> int:
        return self._time

    def put_artifact(
        self,
        artifact_id: str,
        data: bytes,
        *,
        expected_version: int | None = None,
    ) -> dict[str, int | str]:
        self._advance()
        self._fault_state.put_attempts += 1
        if self.config.faults.persistent_failure:
            raise RuntimeError("simulated persistent failure")
        if self._fault_state.put_attempts <= self.config.faults.transient_put_failures:
            self.metrics.simulated_retries += 1
            raise RuntimeError("simulated transient put failure")
        if self.config.faults.partial_write_failure:
            raise RuntimeError("simulated partial write before commit")
        existing = self._objects.get(artifact_id)
        if expected_version is not None and (
            existing is None or existing.version != expected_version
        ):
            raise ValueError("conditional put failed")
        if (
            existing is not None
            and self.config.idempotent_put
            and existing.sha256 == _sha256(data)
        ):
            return {
                "artifact_id": artifact_id,
                "sha256": existing.sha256,
                "version": existing.version,
            }
        version = 1 if existing is None else existing.version + 1
        visible_delay = 0 if self.config.consistency.strong_read_after_write else (
            self.config.consistency.visibility_delay_ticks
        )
        if visible_delay:
            self.metrics.simulated_consistency_delays += 1
        self._objects[artifact_id] = _ObjectRecord(
            data=data,
            sha256=_sha256(data),
            version=version,
            visible_at=self._time + visible_delay,
        )
        self.metrics.simulated_puts += 1
        self.metrics.simulated_bytes_written += len(data)
        if self._write_gbps_for(len(data)) > self.config.write_gbps:
            self.metrics.simulated_write_throttle_events += 1
        return {"artifact_id": artifact_id, "sha256": _sha256(data), "version": version}

    def get_artifact(self, artifact_id: str) -> bytes:
        self._advance()
        self._fault_state.get_attempts += 1
        if self.config.faults.persistent_failure:
            raise RuntimeError("simulated persistent failure")
        if self._fault_state.get_attempts <= self.config.faults.transient_get_failures:
            self.metrics.simulated_retries += 1
            raise RuntimeError("simulated transient get failure")
        record = self._visible_record(artifact_id)
        data = record.data
        if (
            self.config.faults.corrupt_read_after is not None
            and self._fault_state.get_attempts >= self.config.faults.corrupt_read_after
        ):
            data = data + b"corrupt"
            self._fault_state.corruptions_triggered += 1
            if self.config.content_hash_validation and _sha256(data) != record.sha256:
                self.metrics.simulated_corruptions_detected += 1
                raise ValueError("simulated corrupt read detected")
        self.metrics.simulated_gets += 1
        self.metrics.simulated_bytes_read += len(record.data)
        if self._read_gbps_for(len(record.data)) > self.config.read_gbps:
            self.metrics.simulated_read_throttle_events += 1
        return data

    def get_range(self, artifact_id: str, offset: int, length: int) -> bytes:
        if offset < 0 or length <= 0:
            raise ValueError("invalid range")
        data = self.get_artifact(artifact_id)
        if offset + length > len(data):
            raise ValueError("range out of bounds")
        self.metrics.simulated_range_gets += 1
        return data[offset : offset + length]

    def list_artifacts(self) -> list[str]:
        self._advance()
        self.metrics.simulated_lists += 1
        cutoff = max(0, self._time - self.config.consistency.stale_list_ticks)
        return sorted(
            key
            for key, record in self._objects.items()
            if record.visible_at <= cutoff and record.deleted_at is None
        )

    def delete_artifact(self, artifact_id: str) -> None:
        self._advance()
        record = self._objects.get(artifact_id)
        if record is None:
            if self.config.idempotent_delete:
                return
            raise KeyError(artifact_id)
        record.deleted_at = self._time + (
            self.config.consistency.visibility_delay_ticks if self.config.lifecycle_delete else 0
        )
        self.metrics.simulated_deletes += 1

    def advance_logical_time(self, ticks: int) -> None:
        if ticks < 0:
            raise ValueError("ticks must be nonnegative")
        self._time += ticks
        for key, record in list(self._objects.items()):
            if record.deleted_at is not None and record.deleted_at <= self._time:
                del self._objects[key]

    def _visible_record(self, artifact_id: str) -> _ObjectRecord:
        record = self._objects.get(artifact_id)
        if record is None or record.deleted_at is not None:
            raise KeyError(artifact_id)
        if record.visible_at > self._time:
            self.metrics.simulated_consistency_delays += 1
            raise KeyError(f"{artifact_id} not visible yet")
        return record

    def _advance(self) -> None:
        self.advance_logical_time(1)

    def _read_gbps_for(self, byte_count: int) -> float:
        return byte_count * 8 / max(1.0, self.config.get_latency_ms / 1000) / 1_000_000_000

    def _write_gbps_for(self, byte_count: int) -> float:
        return byte_count * 8 / max(1.0, self.config.put_latency_ms / 1000) / 1_000_000_000


def run_remote_backend_simulation(
    *,
    requirements: RemoteBackendRequirementSet,
    config: RemoteBackendSimulatorConfig,
) -> RemoteBackendSimulationReport:
    simulator = LocalRemoteBackendSimulator(config)
    warnings: list[str] = ["simulator only; no real remote backend is enabled"]
    errors: list[str] = []
    data = b"x" * 1024
    try:
        put = simulator.put_artifact("probe", data)
        if config.consistency.strong_read_after_write:
            simulator.get_artifact("probe")
        else:
            try:
                simulator.get_artifact("probe")
            except KeyError:
                pass
            simulator.advance_logical_time(config.consistency.visibility_delay_ticks + 1)
            simulator.get_artifact("probe")
        simulator.get_range("probe", 0, 4)
        simulator.list_artifacts()
        if config.conditional_put:
            try:
                simulator.put_artifact("probe", b"new", expected_version=int(put["version"]) + 1)
            except ValueError:
                pass
        simulator.delete_artifact("probe")
    except Exception as exc:  # noqa: BLE001 - simulation records failures
        errors.append(str(exc))
    throughput = {
        "read_gbps_meets_target": config.read_gbps >= requirements.peak_artifact_read_gbps,
        "write_gbps_meets_target": config.write_gbps >= requirements.peak_artifact_write_gbps,
        "ops_per_second_meets_target": (
            config.ops_per_second >= requirements.peak_artifact_ops_per_second
        ),
        "target_read_gbps": requirements.peak_artifact_read_gbps,
        "simulated_read_gbps": config.read_gbps,
        "target_write_gbps": requirements.peak_artifact_write_gbps,
        "simulated_write_gbps": config.write_gbps,
    }
    latency = {
        "put_latency_ok": _latency_ok(config.put_latency_ms, requirements.max_put_latency_ms),
        "get_latency_ok": _latency_ok(config.get_latency_ms, requirements.max_get_latency_ms),
        "list_latency_ok": _latency_ok(config.list_latency_ms, requirements.max_list_latency_ms),
        "put_latency_ms": config.put_latency_ms,
        "get_latency_ms": config.get_latency_ms,
        "list_latency_ms": config.list_latency_ms,
    }
    consistency = {
        "read_after_write": (
            config.consistency.strong_read_after_write
            or not requirements.required_read_after_write_consistency
        ),
        "monotonic_manifest_visibility": (
            config.consistency.monotonic_manifest_visibility
            or not requirements.required_monotonic_manifest_visibility
        ),
        "conditional_put": config.conditional_put or not requirements.required_conditional_put,
        "atomic_manifest_commit": (
            config.atomic_manifest_commit or not requirements.required_atomic_manifest_commit
        ),
    }
    integrity = {
        "content_hash_validation": (
            config.content_hash_validation or not requirements.required_content_hash_validation
        ),
        "idempotent_put": config.idempotent_put or not requirements.required_idempotent_put,
        "idempotent_delete": (
            config.idempotent_delete or not requirements.required_idempotent_delete
        ),
    }
    return RemoteBackendSimulationReport(
        config=config.model_dump(mode="json"),
        metrics=simulator.metrics.model_dump(mode="json"),
        throughput_validation=throughput,
        latency_validation=latency,
        consistency_validation=consistency,
        integrity_validation=integrity,
        warnings=warnings,
        errors=errors,
    )


def write_remote_backend_simulation_report(
    path: str | Path,
    report: RemoteBackendSimulationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_remote_backend_simulation_report(path: str | Path) -> RemoteBackendSimulationReport:
    return RemoteBackendSimulationReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _latency_ok(value: float, maximum: float | None) -> bool:
    return maximum is None or value <= maximum
