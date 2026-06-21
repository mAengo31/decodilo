from decodilo.lambda_cloud.approval_gate import LambdaApprovalGateReport
from decodilo.lambda_cloud.launch_blockers import build_lambda_launch_blocker_report
from decodilo.lambda_cloud.readiness_summary import build_lambda_readiness_summary


def test_lambda_launch_blockers_report_missing_evidence_and_disabled_launch() -> None:
    report = build_lambda_launch_blocker_report(
        live_discovery_present=False,
        audit_present=False,
        teardown_present=False,
        budget_manifest_present=False,
        price_reconciliation=None,
        resource_reconciliation=None,
        first_launch_policy=None,
        approval_gate=None,
    )
    categories = {blocker.category for blocker in report.blockers}

    assert "missing_live_discovery" in categories
    assert "launch_code_disabled" in categories
    assert "launch_not_supported_in_current_milestone" in categories
    assert report.launch_allowed is False


def test_lambda_readiness_summary_can_be_fake_lifecycle_candidate_only() -> None:
    report = build_lambda_launch_blocker_report(
        live_discovery_present=True,
        audit_present=True,
        teardown_present=True,
        budget_manifest_present=True,
        price_reconciliation=_passed_price(),
        resource_reconciliation=_passed_resource(),
        first_launch_policy=_passed_policy(),
        approval_gate=LambdaApprovalGateReport(
            approval_status="approved_for_future_fake_launch_lifecycle",
            approval_passed=True,
        ),
        remote_backend_ready=False,
    )
    summary = build_lambda_readiness_summary(
        blocker_report=report,
        approval_passed_for_fake_lifecycle=True,
    )

    assert summary.future_fake_launch_lifecycle_candidate is True
    assert summary.future_real_launch_candidate is False
    assert summary.launch_ready is False
    assert "launch_code_disabled" in summary.blockers


def _passed_price():
    from decodilo.lambda_cloud.price_reconciliation import LambdaPriceReconciliationReport
    from decodilo.lambda_cloud.shape_matcher import LambdaShapeMatch

    return LambdaPriceReconciliationReport(
        price_snapshot_id="snap",
        price_snapshot_source_type="manual_json",
        price_snapshot_age_days=1.0,
        is_sample_data=False,
        selected_gpu_type="H100 SXM",
        selected_gpus_per_instance=8,
        planned_instances=1,
        planned_gpus=8,
        planned_hours=0.5,
        base_estimated_cost=10,
        safety_buffer_percentage=15,
        safety_buffer_adjusted_cost=11.5,
        max_run_budget=50,
        starting_credits=100,
        projected_remaining_credits=88.5,
        price_source_status="fresh",
        price_reconciliation_passed=True,
        shape_match=LambdaShapeMatch(
            requested_gpu_type="H100 SXM",
            requested_gpus_per_instance=8,
            requested_region="us-west-1",
            discovery_source="fake_transport",
            live_api_used=False,
            price_snapshot_id="snap",
            match_status="matched",
        ),
    )


def _passed_resource():
    from decodilo.lambda_cloud.resource_reconciliation import (
        LambdaResourceReconciliationReport,
        LambdaUnmanagedResourceSummary,
    )

    return LambdaResourceReconciliationReport(
        planned_nodes=1,
        discovered_instances=0,
        running_instances=0,
        unmanaged_instances=0,
        unmanaged_billable_instances=0,
        region_matches=True,
        unmanaged_summary=LambdaUnmanagedResourceSummary(),
        resource_reconciliation_passed=True,
        manual_review_required=False,
    )


def _passed_policy():
    from decodilo.lambda_cloud.first_launch_policy import (
        LambdaFirstLaunchPolicy,
        LambdaFirstLaunchPolicyReport,
    )

    return LambdaFirstLaunchPolicyReport(
        policy=LambdaFirstLaunchPolicy(),
        policy_passed=True,
    )
