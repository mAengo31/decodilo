from lambda_m043_helpers import write_m043_inputs

from decodilo.lambda_cloud.m043_report import build_lambda_m043_report_from_path


def test_m043_report_summarizes_future_rotation_decision(tmp_path):
    paths = write_m043_inputs(tmp_path)

    report = build_lambda_m043_report_from_path(paths["decision"])

    assert report.decision_status == "authorize_future_catalog_candidate_rotation_review"
    assert report.selected_shape is not None
    assert report.future_review_allowed is True
    assert report.report_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
