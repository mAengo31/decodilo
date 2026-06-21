import pytest
from lambda_m043_helpers import write_m043_inputs
from pydantic import ValidationError

from decodilo.lambda_cloud.m043_decision_record import (
    LambdaM043DecisionRecord,
    build_lambda_m043_decision_record_from_paths,
)


def test_repeated_capacity_with_alternative_candidate_authorizes_future_rotation(tmp_path):
    paths = write_m043_inputs(tmp_path)

    report = build_lambda_m043_decision_record_from_paths(
        capacity_followup=paths["followup"],
        rotation_rank=paths["rotation"],
        retry_policy=paths["retry"],
        operator_selection=paths["selection"],
    )

    assert report.decision_status == "authorize_future_catalog_candidate_rotation_review"
    assert report.selected_shape is not None
    assert report.future_review_allowed is True
    assert report.launch_authorized_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_forbidden_decision_status_rejected():
    with pytest.raises(ValidationError):
        LambdaM043DecisionRecord(
            decision_status="launch_now",
            future_review_allowed=False,
        )
