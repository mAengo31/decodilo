from lambda_m037r_helpers import discovery
from lambda_m038_helpers import canonical_readiness

from decodilo.lambda_cloud.lower_cost_final_state_snapshot import (
    build_lambda_lower_cost_final_state_snapshot,
)


def test_lower_cost_state_snapshot_passes_with_zero_unmanaged():
    report = build_lambda_lower_cost_final_state_snapshot(
        discovery=discovery(),
        canonical_readiness=canonical_readiness(),
    )

    assert report.snapshot_passed is True
    assert report.required_endpoint_success is True
    assert report.unmanaged_billable_count == 0
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_state_snapshot_blocks_unmanaged():
    report = build_lambda_lower_cost_final_state_snapshot(
        discovery=discovery(unmanaged=("i-unmanaged",)),
        canonical_readiness=canonical_readiness(),
    )

    assert report.snapshot_passed is False
    assert "unmanaged_billable_resources_present" in report.blockers
