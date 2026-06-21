from lambda_m036_helpers import support_response

from decodilo.lambda_cloud.idempotency_semantics_evidence import (
    build_lambda_idempotency_semantics_evidence,
)


def test_idempotency_supported_evidence_validates():
    report = build_lambda_idempotency_semantics_evidence(support_response())

    assert report.idempotency_supported is True
    assert report.idempotency_field_name == "client_token"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_idempotency_unknown_warns_and_keeps_no_retry_policy():
    report = build_lambda_idempotency_semantics_evidence(
        support_response(missing=("launch_idempotency",))
    )

    assert report.idempotency_supported is None
    assert report.warnings

