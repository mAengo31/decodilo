from lambda_m029_helpers import m029_fixture

from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
    arm_lambda_m029_from_package,
)
from decodilo.lambda_cloud.real_mutation_transport import (
    LambdaM029HTTPResponse,
    LambdaM029RealMutationTransport,
    LambdaM029TransportConfig,
)


def test_m029_transport_fake_launch_and_blocks_unknown(tmp_path):
    fx = m029_fixture(tmp_path)
    token = fx["token"]
    transport = fx["transport"]

    payload = transport.request_json(
        operation="launch_one_instance",
        payload={"instance_type_name": "gpu_1x_test", "region_name": "us-west-1"},
        arming_token=token,
        idempotency_key="launch-key",
    )

    assert payload["data"]["instance_ids"][0].startswith("fake-i-")
    assert transport.audit_log[-1].authorization_header_redacted is True

    try:
        transport.request_json(
            operation="restart_instance",
            payload={},
            arming_token=token,
            idempotency_key="bad",
        )
    except Exception as exc:  # noqa: BLE001
        assert "unknown operation" in str(exc) or "denied" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("restart should be denied")


def test_m029_transport_rejects_real_url_without_real_mode():
    real_url = "https://" + "cloud." + "lambdalabs." + "com/api/v1"
    try:
        LambdaM029TransportConfig(base_url=real_url)
    except ValueError as exc:
        assert "explicit real API allowance" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("real URL should require explicit allowance")

    cfg = LambdaM029TransportConfig(
        base_url="memory://lambda-m029-test",
        fake_server_mode=True,
    )
    assert LambdaM029RealMutationTransport(config=cfg).config.fake_server_mode is True


def test_real_transport_accepts_status_only_terminate_success_with_fake_http(tmp_path):
    fx = m029_fixture(tmp_path)
    real_url = "https://" + "cloud." + "lambdalabs." + "com/api/v1"
    token = arm_lambda_m029_from_package(
        run_id="test-status-only-terminate",
        execute_real_launch=True,
        confirm_billable_action=CONFIRM_BILLABLE_ACTION,
        confirm_terminate_required=CONFIRM_TERMINATE_REQUIRED,
        m028_report=fx["m028_report"],
        m029_authorization=fx["m029_authorization"],
        emergency_stop_present=True,
        idempotency_key="terminate-key",
        fake_server_mode=False,
    ).token

    def fake_http_caller(request, body, timeout_seconds):  # noqa: ANN001, ARG001
        assert timeout_seconds == 30.0
        return LambdaM029HTTPResponse(
            status_code=204,
            body=b"",
            headers={"Content-Length": "0"},
        )

    transport = LambdaM029RealMutationTransport(
        config=LambdaM029TransportConfig(
            base_url=real_url,
            allow_real_lambda_api=True,
        ),
        api_key="test-api-key-not-real",
        http_caller=fake_http_caller,
    )

    payload = transport.request_json(
        operation="terminate_owned_instance",
        payload={"instance_ids": ["i-owned"]},
        arming_token=token,
        idempotency_key="terminate-key",
    )

    assert payload == {}
    assert transport.diagnostics_log[-1].response_capture.metadata.status_code == 204
