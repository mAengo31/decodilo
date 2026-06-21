from lambda_m036_helpers import (
    ambiguous,
    endpoint_behavior,
    idempotency,
    response_shape,
    validation,
)

from decodilo.lambda_cloud.endpoint_confidence_upgrade import (
    build_lambda_endpoint_confidence_upgrade,
)


def test_complete_evidence_upgrades_endpoint_confidence_to_high():
    report = build_lambda_endpoint_confidence_upgrade(
        support_validation=validation(),
        endpoint_behavior=endpoint_behavior(),
        response_shape=response_shape(),
        idempotency_semantics=idempotency(),
        ambiguous_response_semantics=ambiguous(),
    )

    assert report.upgraded_confidence == "high"
    assert report.upgrade_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_missing_ambiguous_response_semantics_remains_medium():
    report = build_lambda_endpoint_confidence_upgrade(
        support_validation=validation(),
        endpoint_behavior=endpoint_behavior(),
        response_shape=response_shape(),
        idempotency_semantics=idempotency(),
    )

    assert report.upgraded_confidence == "medium"
    assert report.upgrade_passed is False
    assert "ambiguous_response_semantics_missing" in report.blockers

