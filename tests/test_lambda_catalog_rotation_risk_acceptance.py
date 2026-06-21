import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.catalog_rotation_risk_acceptance import (
    LambdaCatalogRotationRiskAcceptance,
    build_lambda_catalog_rotation_risk_acceptance,
)


def test_catalog_rotation_risk_acceptance_complete_future_only():
    report = build_lambda_catalog_rotation_risk_acceptance(
        accept_selected_candidate=True,
        acknowledge_all=True,
    )

    assert (
        report.acceptance_status
        == "accepted_gpu_8x_a100_80gb_sxm4_for_future_review"
    )
    assert report.acceptance_complete is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_catalog_rotation_risk_acceptance_missing_ack_blocks():
    report = build_lambda_catalog_rotation_risk_acceptance(
        accept_selected_candidate=True,
        acknowledge_all=False,
    )

    assert report.acceptance_status == "not_provided"
    assert any(blocker.startswith("missing_acknowledgement:") for blocker in report.blockers)


def test_catalog_rotation_risk_decline_wait_is_valid():
    report = build_lambda_catalog_rotation_risk_acceptance(decline_wait=True)

    assert report.acceptance_status == "declined_wait_for_live_availability"
    assert report.acceptance_complete is True


def test_catalog_rotation_forbidden_status_rejected():
    with pytest.raises(ValidationError):
        LambdaCatalogRotationRiskAcceptance.model_validate(
            {
                "acceptance_status": "launch_now",
                "acceptance_complete": False,
            }
        )
