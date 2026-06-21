import pytest
from lambda_m044_helpers import write_m044_inputs
from pydantic import ValidationError

from decodilo.lambda_cloud.m044_decision_record import (
    LambdaM044DecisionRecord,
    build_lambda_m044_decision_record_from_paths,
)


def test_m044_decision_authorizes_future_review_only(tmp_path):
    paths = write_m044_inputs(tmp_path)
    report = build_lambda_m044_decision_record_from_paths(
        operator_decision=paths["operator"],
        authorization=paths["authorization_m045"],
    )

    assert report.decision_status == "authorize_future_m045_catalog_rotation_launch_review"
    assert report.future_review_allowed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m044_decision_wait_path(tmp_path):
    paths = write_m044_inputs(tmp_path, accept=False, decline_wait=True)
    report = build_lambda_m044_decision_record_from_paths(
        operator_decision=paths["operator"],
        authorization=paths["authorization_m045"],
    )

    assert report.decision_status == "wait_for_live_availability"
    assert report.future_review_allowed is False


def test_m044_decision_manual_path(tmp_path):
    paths = write_m044_inputs(tmp_path, accept=False, decline_manual=True)
    report = build_lambda_m044_decision_record_from_paths(
        operator_decision=paths["operator"],
        authorization=paths["authorization_m045"],
    )

    assert report.decision_status == "require_manual_candidate_selection"


def test_m044_decision_forbidden_status_rejected():
    with pytest.raises(ValidationError):
        LambdaM044DecisionRecord.model_validate(
            {
                "decision_status": "launch_now",
                "future_review_allowed": False,
            }
        )
