from decodilo.lambda_cloud.m055d_report import LambdaM055DReport


def test_m055d_artifact_keeps_cloud_launch_disabled():
    report = LambdaM055DReport(
        report_passed=True,
        capacity_closeout_status="closed_capacity_unavailable_no_instance_created",
        capacity_rejections_count=1,
        ssh_layer_failures_count=1,
        live_candidate_selection_status="selected_live_candidate",
        selected_candidate="gpu_1x_a10",
        selected_region="us-east-1",
        retry_policy_status="policy_passed",
        operator_decision_status="authorize_future_live_candidate_ssh_retry_review",
        m056_authorization_status=(
            "authorized_for_future_m056_live_candidate_ssh_retry_review"
        ),
        command_preview_status="ready_for_future_m056_live_candidate_ssh_retry_review",
        same_candidate_region_retry_blocked=True,
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
