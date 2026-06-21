import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.catalog_availability_risk_acceptance import (
    LambdaCatalogAvailabilityRiskAcceptanceReport,
    build_lambda_catalog_availability_risk_acceptance,
)


def test_missing_acknowledgement_blocks_catalog_risk_acceptance():
    report = build_lambda_catalog_availability_risk_acceptance(accept_risk=True)

    assert report.acceptance_status == "not_provided"
    assert report.acceptance_complete_for_m042_review is False
    assert "missing acknowledgement" in report.blockers[0]
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_complete_catalog_risk_acceptance_is_future_only():
    report = build_lambda_catalog_availability_risk_acceptance(
        accept_risk=True,
        acknowledge_all=True,
    )

    assert report.acceptance_status == "accepted_for_future_m042_review"
    assert report.acceptance_complete_for_m042_review is True
    assert report.blockers == []
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_declined_catalog_risk_produces_declined_status():
    report = build_lambda_catalog_availability_risk_acceptance(decline_risk=True)

    assert report.acceptance_status == "declined_wait_for_live_availability"
    assert report.blockers == []
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_forbidden_catalog_risk_status_rejected():
    with pytest.raises(ValidationError):
        LambdaCatalogAvailabilityRiskAcceptanceReport(
            acceptance_status="launch_now",
            launch_ready=False,
            launch_allowed=False,
        )
