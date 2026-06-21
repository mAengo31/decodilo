"""Remote backend design validation against requirements and simulator evidence."""

from __future__ import annotations

from decodilo.storage.remote_backend_contract import (
    RemoteArtifactBackendCapabilities,
    validate_remote_backend_contract,
)
from decodilo.storage.remote_backend_cost import RemoteBackendCostEstimate
from decodilo.storage.remote_backend_lifecycle import (
    RemoteBackendLifecycleValidationReport,
    validate_remote_backend_lifecycle,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet
from decodilo.storage.remote_backend_security import (
    RemoteBackendSecurityReport,
    evaluate_remote_backend_security,
)
from decodilo.storage.remote_backend_simulator import RemoteBackendSimulationReport


def validate_remote_backend_design(
    *,
    requirements: RemoteBackendRequirementSet,
    simulation: RemoteBackendSimulationReport,
    capabilities: RemoteArtifactBackendCapabilities | None = None,
    security: RemoteBackendSecurityReport | None = None,
    lifecycle: RemoteBackendLifecycleValidationReport | None = None,
    cost: RemoteBackendCostEstimate | None = None,
) -> dict:
    active_capabilities = capabilities or _capabilities_from_simulation(simulation)
    contract = validate_remote_backend_contract(
        capabilities=active_capabilities,
        requirements=requirements,
    )
    active_security = security or evaluate_remote_backend_security(requirements=requirements)
    active_lifecycle = lifecycle or validate_remote_backend_lifecycle(requirements=requirements)
    blockers: list[str] = []
    warnings: list[str] = [
        "simulation pass is not production proof",
        "no real remote artifact backend exists",
    ]
    throughput = simulation.throughput_validation
    for key in [
        "read_gbps_meets_target",
        "write_gbps_meets_target",
        "ops_per_second_meets_target",
    ]:
        if not throughput.get(key):
            blockers.append(key)
    for key, ok in simulation.consistency_validation.items():
        if not ok:
            blockers.append(f"consistency:{key}")
    for key, ok in simulation.integrity_validation.items():
        if not ok:
            blockers.append(f"integrity:{key}")
    if contract.missing_capabilities:
        blockers.extend(f"missing_capability:{item}" for item in contract.missing_capabilities)
    if not active_security.passed:
        blockers.extend(f"security:{error}" for error in active_security.errors)
    if not active_lifecycle.passed:
        blockers.extend(f"lifecycle:{error}" for error in active_lifecycle.errors)
    if simulation.errors:
        blockers.extend(f"simulation:{error}" for error in simulation.errors)
    if cost is not None and requirements.max_monthly_storage_cost is not None:
        monthly = cost.storage_cost_per_hour * 24 * 30
        if monthly > requirements.max_monthly_storage_cost:
            blockers.append("cost:monthly storage budget exceeded")
    status = "simulation_only_passed" if not blockers else "not_ready"
    return {
        "contract": contract.model_dump(mode="json"),
        "security": active_security.model_dump(mode="json"),
        "lifecycle": active_lifecycle.model_dump(mode="json"),
        "cost": cost.model_dump(mode="json") if cost is not None else None,
        "blockers": blockers,
        "warnings": warnings,
        "design_status": status,
    }


def _capabilities_from_simulation(
    simulation: RemoteBackendSimulationReport,
) -> RemoteArtifactBackendCapabilities:
    config = simulation.config
    consistency = config.get("consistency", {})
    return RemoteArtifactBackendCapabilities(
        backend_name="local_remote_backend_simulator",
        remote_backend_enabled=False,
        supports_range_read=True,
        supports_conditional_put=bool(config.get("conditional_put")),
        supports_strong_read_after_write=bool(consistency.get("strong_read_after_write")),
        supports_atomic_manifest_commit=bool(config.get("atomic_manifest_commit")),
        supports_object_versioning=bool(consistency.get("object_versioning")),
        supports_server_side_encryption=False,
        supports_client_side_encryption=False,
        supports_lifecycle_rules=bool(config.get("lifecycle_delete")),
        supports_delete_transactions=False,
        supports_idempotent_put=bool(config.get("idempotent_put")),
        supports_idempotent_delete=bool(config.get("idempotent_delete")),
        supports_integrity_metadata=bool(config.get("content_hash_validation")),
        supports_auth_scopes=bool(config.get("auth_scopes")),
        supports_bandwidth_accounting=True,
        supports_cost_accounting=True,
    )
