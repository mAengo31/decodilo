from lambda_m037r_helpers import discovery, launch_plan, price_reconciliation
from lambda_m038_helpers import canonical_readiness, resource_reconciliation

from decodilo.lambda_cloud.lower_cost_canonical_readiness import (
    build_lambda_lower_cost_canonical_readiness,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import select_existing_lambda_ssh_key


def test_lower_cost_canonical_readiness_passes_with_endpoint_inconclusive():
    report = canonical_readiness()

    assert report.readiness_passed is True
    assert report.shape == "gpu_1x_h100_pcie"
    assert report.quantity == 1
    assert report.selected_ssh_key_hash is not None
    assert report.live_availability_status == "endpoint_inconclusive"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_canonical_readiness_blocks_missing_ssh_key():
    missing = select_existing_lambda_ssh_key(discovery=discovery(ssh_key_names=()))
    report = build_lambda_lower_cost_canonical_readiness(
        launch_plan=launch_plan(),
        ssh_key_selection=missing,
        price_reconciliation=price_reconciliation(),
        resource_reconciliation=resource_reconciliation(),
    )

    assert report.readiness_passed is False
    assert "no existing SSH key names discovered or selected" in report.blockers


def test_lower_cost_canonical_readiness_blocks_sample_price():
    report = canonical_readiness(sample_price=True)

    assert report.readiness_passed is False
    assert "sample_price_snapshot_cannot_support_future_lower_cost_review" in report.blockers
