from lambda_m037r_helpers import ssh_selection
from lambda_m040_helpers import plan, rank

from decodilo.lambda_cloud.availability_first_launch_plan import (
    build_lambda_availability_first_launch_plan,
)


def test_live_candidate_region_plan_is_strand_compatible():
    report = plan(live=True)

    assert report.plan_passed is True
    assert report.plan is not None
    assert report.plan.selected_shape == "gpu_1x_h100_pcie"
    assert report.plan.selected_region == "us-west-1"
    assert report.plan.strand_payload_compatible is True
    assert report.plan.launch_ready is False
    assert report.plan.launch_allowed is False


def test_catalog_only_plan_requires_risk_acceptance():
    report = plan(live=False)

    assert report.plan_passed is True
    assert report.plan is not None
    assert report.plan.risk_acceptance_required is True
    assert report.plan.region_selection_mode == "fixed_region"


def test_missing_region_when_auto_select_claimed_but_not_supported_blocks():
    ranking = rank(live=False)
    report = build_lambda_availability_first_launch_plan(
        rank=ranking,
        ssh_key_selection=ssh_selection(),
        default_region="",
    )

    assert report.plan_passed is False
    assert "availability_first_plan_not_strand_payload_compatible" in report.blockers
    assert report.launch_ready is False
    assert report.launch_allowed is False
