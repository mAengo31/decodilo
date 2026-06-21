from decodilo.lambda_cloud.m029_response_loss_hardening import (
    build_lambda_m029_response_loss_hardening_report,
    candidate_matches_response_loss_policy,
)


def test_response_loss_policy_disallows_auto_retry():
    report = build_lambda_m029_response_loss_hardening_report()

    assert report.auto_retry_launch_allowed is False
    assert report.ambiguity_blocks_termination is True
    assert report.launch_allowed is False


def test_candidate_matching_by_shape_and_region():
    assert candidate_matches_response_loss_policy(
        {"instance_type": "gpu_8x_h100_sxm", "region": "us-west-1"},
        planned_shape="gpu_8x_h100_sxm",
        planned_region="us-west-1",
    )


def test_candidate_mismatch_fails():
    assert not candidate_matches_response_loss_policy(
        {"instance_type": "gpu_1x_h100_pcie", "region": "us-west-1"},
        planned_shape="gpu_8x_h100_sxm",
        planned_region="us-west-1",
    )
