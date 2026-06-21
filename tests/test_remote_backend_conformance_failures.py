import pytest

from decodilo.storage.remote_backend_conformance import (
    passing_simulator_config,
    run_remote_backend_conformance_suite,
)
from decodilo.storage.remote_backend_consistency import RemoteBackendConsistencyConfig
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


def _requirements() -> RemoteBackendRequirementSet:
    return RemoteBackendRequirementSet(
        scenario_id="m016-conformance-failures",
        target_learner_count=4,
        stress_learner_count=8,
        peak_artifact_read_gbps=2,
        peak_artifact_write_gbps=2,
        peak_artifact_ops_per_second=20,
        peak_syncer_merge_gbps=1,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )


@pytest.mark.parametrize(
    ("updates", "expected_case"),
    [
        ({"conditional_put": False}, "conditional_put_conflict"),
        (
            {
                "consistency": RemoteBackendConsistencyConfig(
                    strong_read_after_write=False,
                    monotonic_manifest_visibility=False,
                    object_versioning=True,
                )
            },
            "consistency_read_after_write",
        ),
        ({"content_hash_validation": False}, "integrity_corrupt_read_detected"),
        ({"lifecycle_delete": False}, "lifecycle_delete_transaction"),
        ({"auth_scopes": []}, "security_symbolic_scopes"),
        ({"read_gbps": 0.1, "write_gbps": 0.1}, "bandwidth_and_cost_accounting"),
    ],
)
def test_failing_profiles_fail_expected_cases(updates, expected_case: str) -> None:
    requirements = _requirements()
    config = passing_simulator_config(requirements).model_copy(update=updates)

    report = run_remote_backend_conformance_suite(
        requirements=requirements,
        simulator_config=config,
    )

    assert report.passed is False
    assert expected_case in report.failed_cases
