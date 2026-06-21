from lambda_m044h_helpers import write_m044h_inputs

from decodilo.lambda_cloud.m044h_report import load_lambda_m044h_report


def test_cloud_still_disabled_m044h(tmp_path):
    paths = write_m044h_inputs(tmp_path)
    report = load_lambda_m044h_report(paths["m044h"])

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
