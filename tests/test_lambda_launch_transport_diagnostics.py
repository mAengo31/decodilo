from decodilo.lambda_cloud.launch_transport_diagnostics import (
    build_lambda_launch_transport_diagnostics,
)


def test_timeout_vs_malformed_response_distinguished():
    timeout = build_lambda_launch_transport_diagnostics(exception_type="TimeoutError")
    malformed = build_lambda_launch_transport_diagnostics(
        http_status=200,
        response_content_type="text/html",
        response_body_size=12,
        parse_failed=True,
    )

    assert timeout.failure_kind == "timeout"
    assert timeout.socket_timeout_distinguished is True
    assert malformed.failure_kind == "malformed_response"
    assert malformed.parse_failure_distinguished is True


def test_status_code_and_secret_redaction():
    report = build_lambda_launch_transport_diagnostics(
        http_status=500,
        response_headers={"Authorization": "Bearer lambda_12345678901234567890"},
    )

    assert report.failure_kind == "http_error"
    assert "Bearer" not in str(report.model_dump(mode="json"))
    assert "lambda_12345678901234567890" not in str(report.model_dump(mode="json"))
