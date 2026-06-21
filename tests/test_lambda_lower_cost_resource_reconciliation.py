from lambda_m037r_helpers import discovery, launch_plan, ssh_selection

from decodilo.lambda_cloud.lower_cost_resource_reconciliation import (
    reconcile_lambda_lower_cost_resources,
)
from decodilo.lambda_cloud.strand_lower_cost_launch_plan import (
    build_lambda_strand_lower_cost_launch_plan,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import select_existing_lambda_ssh_key


def test_resource_reconciliation_allows_endpoint_inconclusive_with_key_and_no_unmanaged():
    report = reconcile_lambda_lower_cost_resources(
        discovery=discovery(ssh_key_names=("existing-key",)),
        launch_plan=launch_plan(),
        ssh_key_selection=ssh_selection(),
    )

    assert report.resource_reconciliation_passed is True
    assert report.shape_live_availability_status == "endpoint_inconclusive"
    assert report.unmanaged_billable_count == 0
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_resource_reconciliation_blocks_unmanaged_billable_resources():
    report = reconcile_lambda_lower_cost_resources(
        discovery=discovery(unmanaged=("i-unmanaged",)),
        launch_plan=launch_plan(),
        ssh_key_selection=ssh_selection(),
    )

    assert report.resource_reconciliation_passed is False
    assert "unmanaged_billable_resources_present" in report.errors


def test_resource_reconciliation_blocks_missing_ssh_key_selection():
    missing = select_existing_lambda_ssh_key(discovery=discovery(ssh_key_names=()))
    failed_plan = build_lambda_strand_lower_cost_launch_plan(ssh_key_selection=missing)
    report = reconcile_lambda_lower_cost_resources(
        discovery=discovery(ssh_key_names=()),
        launch_plan=failed_plan,
        ssh_key_selection=missing,
    )

    assert report.resource_reconciliation_passed is False
    assert report.ssh_key_selection_status == "failed"
