"""Stable report for remote backend design validation."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet
from decodilo.storage.remote_backend_simulator import RemoteBackendSimulationReport
from decodilo.storage.remote_backend_validation import validate_remote_backend_design


class RemoteBackendRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    design_status: Literal[
        "not_ready",
        "simulation_only_passed",
        "requires_real_backend_implementation",
    ]
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False


class RemoteBackendDesignValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    created_at_utc: str | None = None
    scenario_id: str
    source_scaling_report_ref: str | None = None
    requirement_set: dict[str, Any]
    backend_capabilities: dict[str, Any]
    simulator_config: dict[str, Any]
    throughput_validation: dict[str, Any]
    latency_validation: dict[str, Any]
    consistency_validation: dict[str, Any]
    integrity_validation: dict[str, Any]
    idempotency_validation: dict[str, Any]
    lifecycle_validation: dict[str, Any]
    replay_checkpoint_validation: dict[str, Any]
    cost_validation: dict[str, Any] | None = None
    security_validation: dict[str, Any]
    gaps: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendation: RemoteBackendRecommendation

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_remote_backend_design_report(
    *,
    requirements: RemoteBackendRequirementSet,
    simulation: RemoteBackendSimulationReport,
    source_scaling_report_ref: str | None = None,
) -> RemoteBackendDesignValidationReport:
    validation = validate_remote_backend_design(
        requirements=requirements,
        simulation=simulation,
    )
    contract = validation["contract"]
    security = validation["security"]
    lifecycle = validation["lifecycle"]
    blockers = validation["blockers"]
    status = validation["design_status"]
    return RemoteBackendDesignValidationReport(
        created_at_utc=datetime.now(UTC).isoformat(),
        scenario_id=requirements.scenario_id,
        source_scaling_report_ref=source_scaling_report_ref,
        requirement_set=requirements.model_dump(mode="json"),
        backend_capabilities=contract,
        simulator_config=simulation.config,
        throughput_validation=simulation.throughput_validation,
        latency_validation=simulation.latency_validation,
        consistency_validation=simulation.consistency_validation,
        integrity_validation=simulation.integrity_validation,
        idempotency_validation={
            "idempotent_put": simulation.integrity_validation.get("idempotent_put"),
            "idempotent_delete": simulation.integrity_validation.get("idempotent_delete"),
        },
        lifecycle_validation=lifecycle,
        replay_checkpoint_validation={
            "required_replay_snapshot_frequency": (
                requirements.required_replay_snapshot_frequency
            ),
            "checkpoint_storage_growth_gb_per_hour": (
                requirements.checkpoint_storage_growth_gb_per_hour
            ),
        },
        security_validation=security,
        gaps=contract.get("missing_capabilities", []),
        blockers=blockers,
        warnings=validation["warnings"],
        recommendation=RemoteBackendRecommendation(design_status=status),
    )


def write_remote_backend_design_report(
    path: str | Path,
    report: RemoteBackendDesignValidationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_remote_backend_design_report(path: str | Path) -> RemoteBackendDesignValidationReport:
    return RemoteBackendDesignValidationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )

