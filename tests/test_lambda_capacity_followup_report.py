from lambda_m043_helpers import write_m043_inputs

from decodilo.lambda_cloud.capacity_followup_report import (
    build_lambda_capacity_followup_from_paths,
)


def test_capacity_followup_closes_teardown_risk_when_no_instance_created(tmp_path):
    paths = write_m043_inputs(tmp_path)
    report = build_lambda_capacity_followup_from_paths(
        history=paths["history"],
        latest_closeout=paths["latest_closeout"],
        latest_discovery=paths["discovery"],
    )

    assert report.latest_closeout_status == "closed_capacity_unavailable_no_instance_created"
    assert report.teardown_risk_status == "no_teardown_required_no_instance_created"
    assert report.termination_required is False
    assert report.same_fixed_shape_retry_blocked is True
    assert report.repeated_capacity_error_detected is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_capacity_followup_recommends_rotation_for_repeated_capacity(tmp_path):
    paths = write_m043_inputs(tmp_path)
    report = build_lambda_capacity_followup_from_paths(
        history=paths["history"],
        latest_closeout=paths["latest_closeout"],
    )

    assert report.recommended_strategy == "rotate_catalog_candidate"
