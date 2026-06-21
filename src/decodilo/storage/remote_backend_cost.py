"""Manual planning cost model for future remote artifact backend traffic."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


class RemoteBackendTrafficEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact_bytes_written_per_hour: float = Field(ge=0)
    artifact_bytes_read_per_hour: float = Field(ge=0)
    range_read_ops_per_hour: float = Field(ge=0)
    put_ops_per_hour: float = Field(ge=0)
    list_ops_per_hour: float = Field(ge=0)
    delete_ops_per_hour: float = Field(ge=0)
    storage_retained_gb_hours: float = Field(ge=0)
    egress_gb_per_hour: float = Field(default=0.0, ge=0)


class RemoteBackendCostModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    storage_cost_per_gb_hour: float | None = Field(default=None, ge=0)
    read_cost_per_1000_ops: float | None = Field(default=None, ge=0)
    write_cost_per_1000_ops: float | None = Field(default=None, ge=0)
    list_cost_per_1000_ops: float | None = Field(default=None, ge=0)
    delete_cost_per_1000_ops: float | None = Field(default=None, ge=0)
    egress_cost_per_gb: float | None = Field(default=None, ge=0)
    fail_on_missing_price: bool = False


class RemoteBackendCostEstimate(BaseModel):
    model_config = ConfigDict(frozen=True)

    storage_cost_per_hour: float
    read_ops_cost_per_hour: float
    write_ops_cost_per_hour: float
    list_ops_cost_per_hour: float
    delete_ops_cost_per_hour: float
    egress_cost_per_hour: float
    total_backend_cost_per_hour: float
    backend_cost_per_useful_token: float | None = None
    warnings: list[str] = Field(default_factory=list)
    planning_estimate: bool = True

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def estimate_remote_backend_cost(
    *,
    requirements: RemoteBackendRequirementSet,
    cost_model: RemoteBackendCostModel,
    useful_tokens_per_hour: float | None = None,
) -> RemoteBackendCostEstimate:
    traffic = traffic_from_requirements(requirements)
    warnings: list[str] = ["manual planning estimate; no live pricing API used"]
    if cost_model.fail_on_missing_price and any(
        value is None
        for value in [
            cost_model.storage_cost_per_gb_hour,
            cost_model.read_cost_per_1000_ops,
            cost_model.write_cost_per_1000_ops,
            cost_model.list_cost_per_1000_ops,
            cost_model.delete_cost_per_1000_ops,
            cost_model.egress_cost_per_gb,
        ]
    ):
        raise ValueError("cost profile is missing required prices")
    storage = traffic.storage_retained_gb_hours * _price(
        cost_model.storage_cost_per_gb_hour,
        "storage price missing",
        warnings,
    )
    read = traffic.range_read_ops_per_hour / 1000 * _price(
        cost_model.read_cost_per_1000_ops,
        "read op price missing",
        warnings,
    )
    write = traffic.put_ops_per_hour / 1000 * _price(
        cost_model.write_cost_per_1000_ops,
        "write op price missing",
        warnings,
    )
    list_cost = traffic.list_ops_per_hour / 1000 * _price(
        cost_model.list_cost_per_1000_ops,
        "list op price missing",
        warnings,
    )
    delete = traffic.delete_ops_per_hour / 1000 * _price(
        cost_model.delete_cost_per_1000_ops,
        "delete op price missing",
        warnings,
    )
    egress = traffic.egress_gb_per_hour * _price(
        cost_model.egress_cost_per_gb,
        "egress price missing",
        warnings,
    )
    total = storage + read + write + list_cost + delete + egress
    return RemoteBackendCostEstimate(
        storage_cost_per_hour=storage,
        read_ops_cost_per_hour=read,
        write_ops_cost_per_hour=write,
        list_ops_cost_per_hour=list_cost,
        delete_ops_cost_per_hour=delete,
        egress_cost_per_hour=egress,
        total_backend_cost_per_hour=total,
        backend_cost_per_useful_token=(
            total / useful_tokens_per_hour
            if useful_tokens_per_hour is not None and useful_tokens_per_hour > 0
            else None
        ),
        warnings=warnings,
    )


def traffic_from_requirements(
    requirements: RemoteBackendRequirementSet,
) -> RemoteBackendTrafficEstimate:
    read_bytes = requirements.peak_artifact_read_gbps * 1_000_000_000 / 8 * 3600
    write_bytes = requirements.peak_artifact_write_gbps * 1_000_000_000 / 8 * 3600
    ops = requirements.peak_artifact_ops_per_second * 3600
    return RemoteBackendTrafficEstimate(
        artifact_bytes_written_per_hour=write_bytes,
        artifact_bytes_read_per_hour=read_bytes,
        range_read_ops_per_hour=ops * 0.6,
        put_ops_per_hour=ops * 0.3,
        list_ops_per_hour=ops * 0.05,
        delete_ops_per_hour=ops * 0.05,
        storage_retained_gb_hours=requirements.checkpoint_storage_growth_gb_per_hour,
        egress_gb_per_hour=read_bytes / (1024**3),
    )


def load_remote_backend_cost_model(path: str | Path) -> RemoteBackendCostModel:
    return RemoteBackendCostModel.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_cost_estimate(
    path: str | Path,
    estimate: RemoteBackendCostEstimate,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(estimate.to_json(), encoding="utf-8")


def _price(value: float | None, warning: str, warnings: list[str]) -> float:
    if value is None:
        warnings.append(warning)
        return 0.0
    return value

