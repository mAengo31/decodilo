import pytest
from lambda_m037r_helpers import discovery, ssh_selection

from decodilo.lambda_cloud.strand_lower_cost_launch_plan import (
    LambdaStrandLowerCostLaunchPlan,
    build_lambda_strand_lower_cost_launch_plan,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import select_existing_lambda_ssh_key


def test_valid_lower_cost_plan_uses_strand_payload_shape():
    report = build_lambda_strand_lower_cost_launch_plan(ssh_key_selection=ssh_selection())

    assert report.plan_passed is True
    assert report.plan is not None
    assert report.plan.to_strand_payload() == {
        "region_name": "us-west-1",
        "instance_type_name": "gpu_1x_h100_pcie",
        "ssh_key_names": ["existing-key"],
        "quantity": 1,
    }
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_missing_ssh_key_blocks_plan():
    selection = select_existing_lambda_ssh_key(discovery=discovery(ssh_key_names=()))
    report = build_lambda_strand_lower_cost_launch_plan(ssh_key_selection=selection)

    assert report.plan_passed is False
    assert "existing_ssh_key_name_required_for_strand_launch" in report.blockers


def test_setup_or_cloud_init_fields_are_rejected_by_schema():
    with pytest.raises(ValueError):
        LambdaStrandLowerCostLaunchPlan(
            region_name="us-west-1",
            ssh_key_names=["existing-key"],
            cloud_init_allowed=True,
        )
