import json

from lambda_m043_helpers import write_m043_inputs

from decodilo.lambda_cloud.capacity_aware_report_semantics import (
    build_lambda_capacity_aware_run_semantics_from_path,
)


def test_capacity_error_maps_to_no_teardown_required(tmp_path):
    paths = write_m043_inputs(tmp_path)

    report = build_lambda_capacity_aware_run_semantics_from_path(paths["latest_closeout"])

    assert report.launch_outcome == "capacity_rejected_no_instance_created"
    assert report.termination_required is False
    assert report.ownership_uncertain is False
    assert report.manual_review_required_for_teardown is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_response_loss_maps_to_manual_review(tmp_path):
    paths = write_m043_inputs(tmp_path)
    data = json.loads(paths["latest_closeout"].read_text(encoding="utf-8"))
    data["status_code"] = None
    data["capacity_error_confirmed"] = False
    data["closeout_succeeded"] = False
    data["blockers"] = ["launch_response_missing_or_lost"]
    paths["latest_closeout"].write_text(json.dumps(data), encoding="utf-8")

    report = build_lambda_capacity_aware_run_semantics_from_path(paths["latest_closeout"])

    assert report.launch_outcome == "response_loss_manual_review_required"
    assert report.manual_review_required_for_teardown is True
