from lambda_m029_helpers import m029_fixture

from decodilo.lambda_cloud.http_response_capture import capture_lambda_http_response
from decodilo.lambda_cloud.m029_report import build_m029_report
from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnostics,
)
from decodilo.lambda_cloud.real_launch_spend_audit import build_m029_spend_audit


def test_m029_report_fake_success_flags_false(tmp_path):
    fx = m029_fixture(tmp_path)
    launch, ledger = fx["launch_executor"].launch_one_instance(
        resource_lock=fx["resource"],
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].launch_key.idempotency_key,
    )
    term, _ledger = fx["termination_executor"].terminate_owned_instance(
        owned_instance_id=launch.owned_instance_id,
        ledger=ledger,
        arming_token=fx["token"],
        idempotency_key=fx["idempotency"].terminate_key.idempotency_key,
    )
    spend = build_m029_spend_audit(
        estimated_hourly_cost=100,
        elapsed_seconds=1,
        launch_request_sent=True,
        terminate_request_sent=True,
        termination_verified=True,
        billable_action_performed=False,
    )

    report = build_m029_report(
        run_id="run",
        launch_result=launch,
        termination_result=term,
        spend_audit=spend,
        elapsed_seconds=1,
    )

    assert report.termination_verified is True
    assert report.billable_action_performed is False
    assert report.launch_allowed is False


def test_m029_report_persists_redacted_provider_error_message():
    capture = capture_lambda_http_response(
        method="POST",
        endpoint_path_template="/instance-operations/launch",
        endpoint_path="/instance-operations/launch",
        mutation_operation_name="launch_one_instance",
        status_code=400,
        headers={"Content-Type": "application/json"},
        body=b'{"error":{"message":"bad request"}}',
    )
    diagnostic = LambdaMutationTransportDiagnostics(
        operation="launch_one_instance",
        stages=["request_sent", "status_received", "exception_raised"],
        response_capture=capture,
    )
    spend = build_m029_spend_audit(
        estimated_hourly_cost=3.29,
        elapsed_seconds=1,
        launch_request_sent=True,
        terminate_request_sent=False,
        termination_verified=False,
        billable_action_performed=True,
    )

    report = build_m029_report(
        run_id="run",
        launch_result=None,
        termination_result=None,
        spend_audit=spend,
        elapsed_seconds=1,
        transport_diagnostics=[diagnostic],
    )

    assert report.launch_response_http_status == 400
    assert report.launch_response_classification == "http_error_json"
    assert report.launch_response_error_message_redacted == "bad request"
    assert report.launch_allowed is False
