from decodilo.lambda_cloud.launch_endpoint_diagnostics import (
    build_lambda_launch_endpoint_diagnostics,
)


def test_known_fixture_endpoint_passes():
    report = build_lambda_launch_endpoint_diagnostics(
        launch_endpoint_path="/instance-operations/launch",
        launch_http_method="POST",
        terminate_endpoint_path="/instance-operations/terminate",
        terminate_http_method="DELETE",
        operation_spec_verified=True,
        docs_or_operator_verified=True,
    )

    assert report.endpoint_diagnostics_passed is True
    assert report.launch_allowed is False


def test_unknown_endpoint_creates_blocker():
    report = build_lambda_launch_endpoint_diagnostics(
        launch_endpoint_path=None,
        launch_http_method="POST",
        terminate_endpoint_path="/instance-operations/terminate",
        terminate_http_method="DELETE",
        operation_spec_verified=True,
    )

    assert report.endpoint_diagnostics_passed is False
    assert "launch endpoint path missing" in report.blockers


def test_non_allowed_method_creates_blocker():
    report = build_lambda_launch_endpoint_diagnostics(
        launch_endpoint_path="/instance-operations/launch",
        launch_http_method="GET",
        terminate_endpoint_path="/instance-operations/terminate",
        terminate_http_method="DELETE",
        operation_spec_verified=True,
    )

    assert report.endpoint_diagnostics_passed is False
    assert "launch method not allowed by M031D diagnostics" in report.blockers
