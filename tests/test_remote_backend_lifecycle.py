from decodilo.storage.remote_backend_lifecycle import (
    RemoteBackendLifecyclePlan,
    validate_remote_backend_lifecycle,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="lifecycle",
        target_learner_count=8,
        stress_learner_count=16,
        peak_artifact_read_gbps=1,
        peak_artifact_write_gbps=1,
        peak_artifact_ops_per_second=1,
        peak_syncer_merge_gbps=1,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


def test_lifecycle_plan_protects_checkpoint_and_global_state() -> None:
    report = validate_remote_backend_lifecycle(requirements=_requirements())

    assert report.passed is True
    assert {rule.name for rule in report.plan.retention_rules} >= {
        "latest_checkpoint",
        "latest_global_state",
    }


def test_lifecycle_requires_delete_transaction() -> None:
    report = validate_remote_backend_lifecycle(
        requirements=_requirements(),
        plan=RemoteBackendLifecyclePlan(transaction_log_required=False),
    )

    assert report.passed is False
    assert any("transaction" in error for error in report.errors)


def test_lifecycle_warns_on_long_cleanup_window() -> None:
    report = validate_remote_backend_lifecycle(
        requirements=_requirements(),
        plan=RemoteBackendLifecyclePlan(lifecycle_cleanup_window_hours=24 * 10),
    )

    assert report.warnings

