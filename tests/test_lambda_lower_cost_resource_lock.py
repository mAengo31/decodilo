from lambda_m037r_helpers import discovery, launch_plan
from lambda_m038_helpers import resource_lock, state_snapshot

from decodilo.lambda_cloud.lower_cost_resource_lock import (
    build_lambda_lower_cost_resource_lock,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import select_existing_lambda_ssh_key


def test_lower_cost_resource_lock_passes_for_existing_key():
    report = resource_lock()

    assert report.resource_lock_passed is True
    assert report.shape_locked == "gpu_1x_h100_pcie"
    assert report.ssh_key_locked is True
    assert report.terminate_scope_future_owned_only is True
    assert report.no_create_delete_resources is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_resource_lock_blocks_missing_ssh_key():
    missing = select_existing_lambda_ssh_key(discovery=discovery(ssh_key_names=()))
    report = build_lambda_lower_cost_resource_lock(
        state_snapshot=state_snapshot(),
        launch_plan=launch_plan(),
        ssh_key_selection=missing,
    )

    assert report.resource_lock_passed is False
    assert "no existing SSH key names discovered or selected" in report.blockers
