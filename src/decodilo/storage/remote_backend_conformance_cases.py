"""Provider-neutral remote backend conformance case definitions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RemoteBackendConformanceCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    category: str
    description: str
    required: bool = True
    expected_failure_profiles: list[str] = Field(default_factory=list)


def default_conformance_cases() -> list[RemoteBackendConformanceCase]:
    return [
        RemoteBackendConformanceCase(
            case_id="basic_artifact_operations",
            category="basic",
            description="put/head/get/range/list/delete operations work in the simulator",
        ),
        RemoteBackendConformanceCase(
            case_id="integrity_corrupt_read_detected",
            category="integrity",
            description="corrupt reads are detected by content-hash validation",
            expected_failure_profiles=["corrupt_reads_not_detected"],
        ),
        RemoteBackendConformanceCase(
            case_id="consistency_read_after_write",
            category="consistency",
            description="declared read-after-write and monotonic manifest visibility hold",
            expected_failure_profiles=[
                "eventual_consistency_without_monotonic_manifest_visibility"
            ],
        ),
        RemoteBackendConformanceCase(
            case_id="conditional_put_conflict",
            category="consistency",
            description="conditional manifest writes reject version mismatch",
            expected_failure_profiles=["no_conditional_put"],
        ),
        RemoteBackendConformanceCase(
            case_id="retry_and_idempotency",
            category="retry_idempotency",
            description="transient failures can be retried and duplicate writes are idempotent",
        ),
        RemoteBackendConformanceCase(
            case_id="partial_write_not_visible",
            category="retry_idempotency",
            description="partial write failure does not commit a visible artifact",
        ),
        RemoteBackendConformanceCase(
            case_id="lifecycle_delete_transaction",
            category="lifecycle_gc",
            description="delete lifecycle has idempotent transaction-safe semantics",
            expected_failure_profiles=["no_delete_transactions"],
        ),
        RemoteBackendConformanceCase(
            case_id="replay_checkpoint_restore",
            category="replay_restore",
            description="checkpoint/replay/event segment bytes can be range-read and validated",
        ),
        RemoteBackendConformanceCase(
            case_id="security_symbolic_scopes",
            category="security",
            description="symbolic authorization scopes exist and no raw secrets are present",
            expected_failure_profiles=["missing_auth_scopes"],
        ),
        RemoteBackendConformanceCase(
            case_id="bandwidth_and_cost_accounting",
            category="bandwidth_cost",
            description="reads/writes/range reads/throttling are accounted",
            expected_failure_profiles=["insufficient_bandwidth"],
        ),
    ]
