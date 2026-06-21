import pytest
from lambda_m045_helpers import write_m045_inputs
from pydantic import ValidationError

from decodilo.lambda_cloud.m045_decision_record import (
    LambdaM045DecisionRecord,
    load_lambda_m045_decision_record,
)


def test_m045_decision_authorizes_future_m046_review_only(tmp_path):
    paths = write_m045_inputs(tmp_path)
    report = load_lambda_m045_decision_record(paths["decision_m045"])

    assert report.decision_status == "authorize_future_m046_capacity_selected_launch_review"
    assert report.selected_candidate == "gpu_8x_a100_80gb_sxm4"
    assert report.future_review_allowed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m045_decision_wait_path(tmp_path):
    paths = write_m045_inputs(tmp_path, approve=False, decline_wait=True)
    report = load_lambda_m045_decision_record(paths["decision_m045"])

    assert report.decision_status == "wait_for_live_availability"
    assert report.future_review_allowed is False


def test_m045_decision_manual_path(tmp_path):
    paths = write_m045_inputs(tmp_path, approve=False, decline_manual=True)
    report = load_lambda_m045_decision_record(paths["decision_m045"])

    assert report.decision_status == "require_manual_candidate_selection"


def test_m045_decision_forbidden_status_rejected():
    with pytest.raises(ValidationError):
        LambdaM045DecisionRecord.model_validate(
            {
                "decision_status": "launch_now",
                "future_review_allowed": False,
            }
        )
