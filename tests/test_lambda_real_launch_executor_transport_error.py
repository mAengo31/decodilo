from lambda_m029_helpers import m029_fixture

from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
    arm_lambda_m029_from_package,
)
from decodilo.lambda_cloud.real_launch_client import LambdaM029RealLaunchClient
from decodilo.lambda_cloud.real_launch_executor import LambdaM029LaunchExecutor
from decodilo.lambda_cloud.real_launch_journal import LambdaM029LaunchJournal
from decodilo.lambda_cloud.real_launch_ledger import LambdaM029LaunchLedger
from decodilo.lambda_cloud.real_mutation_transport import (
    LambdaM029HTTPResponse,
    LambdaM029RealMutationTransport,
    LambdaM029TransportConfig,
)


def test_launch_executor_persists_http_error_as_manual_review_result(tmp_path):
    fx = m029_fixture(tmp_path)
    real_url = "https://" + "cloud." + "lambdalabs." + "com/api/v1"
    token = arm_lambda_m029_from_package(
        run_id="test-m034-http-error",
        execute_real_launch=True,
        confirm_billable_action=CONFIRM_BILLABLE_ACTION,
        confirm_terminate_required=CONFIRM_TERMINATE_REQUIRED,
        m028_report=fx["m028_report"],
        m029_authorization=fx["m029_authorization"],
        emergency_stop_present=True,
        idempotency_key="test-m034-http-error-key",
        fake_server_mode=False,
    ).token
    assert token is not None

    def fake_http_caller(request, body, timeout_seconds):  # noqa: ARG001
        assert timeout_seconds == 30.0
        return LambdaM029HTTPResponse(
            status_code=400,
            body=b'{"error":"bad request"}',
            headers={"Content-Type": "application/json"},
            reason="Bad Request",
        )

    transport = LambdaM029RealMutationTransport(
        config=LambdaM029TransportConfig(
            base_url=real_url,
            timeout_seconds=30.0,
            allow_real_lambda_api=True,
        ),
        api_key="test-api-key-not-real",
        http_caller=fake_http_caller,
    )
    executor = LambdaM029LaunchExecutor(
        client=LambdaM029RealLaunchClient(transport),
        journal=LambdaM029LaunchJournal(tmp_path / "journal.jsonl", run_id="m034"),
        ledger=LambdaM029LaunchLedger(run_id="m034"),
    )
    resource = fx["resource"].model_copy(update={"ssh_key_ref": "existing-key"})

    result, ledger = executor.launch_one_instance(
        resource_lock=resource,
        arming_token=token,
        idempotency_key="test-m034-http-error-key",
    )

    assert result.request_sent is True
    assert result.response_received is True
    assert result.manual_review_required is True
    assert ledger.manual_review_required is True
    assert transport.diagnostics_log[-1].response_capture.metadata.status_code == 400
