from decodilo.lambda_cloud.response_loss_regression_harness import (
    DEFAULT_RESPONSE_LOSS_SCENARIOS,
    run_lambda_response_loss_regression_harness,
)


def test_regression_harness_covers_all_required_scenarios():
    report = run_lambda_response_loss_regression_harness()

    assert report.regression_harness_passed is True
    assert report.all_scenarios_covered is True
    assert set(report.scenarios_completed) == set(DEFAULT_RESPONSE_LOSS_SCENARIOS)
    assert all(result.no_automatic_relaunch for result in report.scenario_results)
    assert all(result.no_unowned_termination for result in report.scenario_results)


def test_regression_harness_distinguishes_response_loss_modes():
    report = run_lambda_response_loss_regression_harness()
    classifications = {result.observed_classification for result in report.scenario_results}

    assert "timeout" in classifications
    assert "success_empty_body" in classifications
    assert "success_non_json" in classifications
    assert "schema_validation_failure" in classifications
    assert "http_error_non_json" in classifications
    assert report.launch_ready is False
    assert report.launch_allowed is False
