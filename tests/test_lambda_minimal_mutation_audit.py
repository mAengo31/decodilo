from lambda_m027_helpers import fake_context

from decodilo.lambda_cloud.fake_server_launch_terminate_flow import (
    LambdaFakeServerLaunchTerminateFlowReport,
    run_fake_server_launch_terminate_flow,
)
from decodilo.lambda_cloud.minimal_mutation_audit import audit_minimal_mutation_flow


def test_clean_fake_flow_audit_passes():
    flow = run_fake_server_launch_terminate_flow(context=fake_context())
    report = audit_minimal_mutation_flow(flow)

    assert report.audit_passed is True
    assert report.fake_execution_only is True
    assert report.real_lambda_api_used is False
    assert report.launch_allowed is False


def test_audit_fails_non_synthetic_id_or_missing_termination():
    flow = LambdaFakeServerLaunchTerminateFlowReport(
        fake_launch_executed=True,
        fake_terminate_executed=False,
        fake_instance_id="live-id",
        launch_idempotency_key="launch",
        terminate_idempotency_key="terminate",
        duplicate_launch_safe=True,
        duplicate_terminate_safe=False,
        termination_verified=False,
    )

    report = audit_minimal_mutation_flow(flow)

    assert report.audit_passed is False
    assert report.blockers
