from lambda_m045_helpers import write_m045_inputs

from decodilo.lambda_cloud.m045_report import load_lambda_m045_report
from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_cloud_still_disabled_m045(tmp_path):
    paths = write_m045_inputs(tmp_path)
    report = load_lambda_m045_report(paths["m045"])

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False


def test_lambda_preflight_loads_m045_report_but_keeps_launch_disabled(tmp_path):
    paths = write_m045_inputs(tmp_path)
    report = run_lambda_preflight(m045_report=paths["m045"])

    assert report.m045_capacity_selected_summary is not None
    assert (
        report.m045_capacity_selected_summary["authorization_status"]
        == "authorized_for_future_m046_capacity_selected_launch_review"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.real_mutation_enabled is False
