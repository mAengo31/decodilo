from decodilo.lambda_cloud.api_error_handling import LambdaEndpointDeniedError
from decodilo.lambda_cloud.api_models import LambdaInstance
from decodilo.lambda_cloud.endpoint_calibration import (
    build_lambda_endpoint_calibration_report,
    endpoint_result_for_failure,
    endpoint_result_for_success,
)
from decodilo.lambda_cloud.read_only_audit import LambdaReadOnlyAuditEntry


def test_lambda_endpoint_calibration_records_success_and_shape() -> None:
    instance = LambdaInstance.model_validate(
        {"instance_id": "i-1", "status": "active", "tags": {}, "new_field": "seen"}
    )
    result = endpoint_result_for_success(
        operation="list_instances",
        payload=[instance],
        audit_entry=LambdaReadOnlyAuditEntry(
            operation="list_instances",
            method="GET",
            endpoint="/instances",
            allowed=True,
            status_code=200,
            live_api_used=True,
        ),
        live_api_used=True,
    )
    report = build_lambda_endpoint_calibration_report([result])

    assert report.endpoint_count_attempted == 1
    assert report.endpoint_count_succeeded == 1
    assert result.mutation is False
    assert result.billable_action_performed is False
    assert result.unknown_fields_seen == ["new_field"]
    assert "items=1" in (result.response_shape_summary or "")


def test_lambda_endpoint_calibration_redacts_failure_message() -> None:
    result = endpoint_result_for_failure(
        operation="list_images",
        exc=RuntimeError("failed with Authorization: Bearer lambda_12345678901234567890"),
        audit_entry=None,
        live_api_used=True,
    )

    assert result.success is False
    assert "Bearer" not in (result.error_message_redacted or "")
    assert result.billable_action_performed is False


def test_lambda_endpoint_calibration_classifies_optional_unsupported() -> None:
    result = endpoint_result_for_failure(
        operation="get_quota",
        exc=LambdaEndpointDeniedError("Lambda endpoint denied or unsupported: 404"),
        audit_entry=LambdaReadOnlyAuditEntry(
            operation="get_quota",
            method="GET",
            endpoint="/quota",
            allowed=True,
            status_code=404,
            live_api_used=True,
            error="404",
        ),
        live_api_used=True,
    )
    report = build_lambda_endpoint_calibration_report([result])

    assert result.endpoint_classification == "unsupported_optional_endpoint"
    assert report.endpoint_count_failed_optional == 1
    assert report.endpoint_count_unsupported_optional == 1
    assert report.required_endpoint_success is True


def test_lambda_endpoint_calibration_required_failure_sets_required_success_false() -> None:
    result = endpoint_result_for_failure(
        operation="list_instances",
        exc=RuntimeError("fixture failure"),
        audit_entry=LambdaReadOnlyAuditEntry(
            operation="list_instances",
            method="GET",
            endpoint="/instances",
            allowed=True,
            status_code=500,
            live_api_used=True,
            error="500",
        ),
        live_api_used=True,
    )
    report = build_lambda_endpoint_calibration_report([result])

    assert report.endpoint_count_failed_required == 1
    assert report.required_endpoint_success is False
