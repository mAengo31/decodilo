from decodilo.storage.remote_backend_cost import (
    RemoteBackendCostModel,
    estimate_remote_backend_cost,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


def _requirements(read: float = 1, write: float = 1) -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="cost",
        target_learner_count=8,
        stress_learner_count=16,
        peak_artifact_read_gbps=read,
        peak_artifact_write_gbps=write,
        peak_artifact_ops_per_second=100,
        peak_syncer_merge_gbps=4,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


def test_increasing_bytes_increases_cost() -> None:
    model = RemoteBackendCostModel(
        storage_cost_per_gb_hour=0.01,
        read_cost_per_1000_ops=0.001,
        write_cost_per_1000_ops=0.001,
        list_cost_per_1000_ops=0.001,
        delete_cost_per_1000_ops=0.001,
        egress_cost_per_gb=0.01,
    )

    low = estimate_remote_backend_cost(requirements=_requirements(1, 1), cost_model=model)
    high = estimate_remote_backend_cost(requirements=_requirements(2, 2), cost_model=model)

    assert high.egress_cost_per_hour > low.egress_cost_per_hour
    assert high.total_backend_cost_per_hour > low.total_backend_cost_per_hour


def test_missing_price_profile_warns() -> None:
    estimate = estimate_remote_backend_cost(
        requirements=_requirements(),
        cost_model=RemoteBackendCostModel(),
    )

    assert estimate.planning_estimate is True
    assert any("missing" in warning for warning in estimate.warnings)

