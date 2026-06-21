import json
import subprocess
import sys

from lambda_m031d_helpers import closed_m031_incident

from decodilo.lambda_cloud.m031_incident_report import write_lambda_m031_incident_report


def _run(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, "-m", "decodilo.cli", *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


def test_response_loss_cli_flow_is_offline(tmp_path):
    incident_path = tmp_path / "m031-incident.json"
    endpoint_out = tmp_path / "endpoint.json"
    fixture_out = tmp_path / "fixture.json"
    regression_out = tmp_path / "regression.json"
    acceptance_out = tmp_path / "acceptance.json"
    hold_out = tmp_path / "hold.json"
    report_out = tmp_path / "m032.json"
    write_lambda_m031_incident_report(incident_path, closed_m031_incident())

    endpoint = _run(
        "lambda",
        "response-loss",
        "endpoint-spec",
        "--operation",
        "launch_one_instance",
        "--method",
        "POST",
        "--path-template",
        "/instance-operations/launch",
        "--terminate-method",
        "POST",
        "--terminate-path-template",
        "/instance-operations/terminate",
        "--source-url",
        "https://docs.lambda.ai/public-cloud/cloud-api/",
        "--confidence",
        "medium",
        "--out",
        str(endpoint_out),
    )
    fixture = _run(
        "lambda",
        "response-loss",
        "diagnostics-fixture",
        "--scenario",
        "launch_status_200_empty_body",
        "--out",
        str(fixture_out),
    )
    regression = _run(
        "lambda",
        "response-loss",
        "regression-harness",
        "--out",
        str(regression_out),
    )
    acceptance = _run(
        "lambda",
        "response-loss",
        "mitigation-acceptance",
        "--endpoint-spec",
        str(endpoint_out),
        "--regression-report",
        str(regression_out),
        "--out",
        str(acceptance_out),
    )
    hold = _run(
        "lambda",
        "response-loss",
        "hold-release",
        "--m031-incident-report",
        str(incident_path),
        "--mitigation-acceptance",
        str(acceptance_out),
        "--out",
        str(hold_out),
    )
    report = _run(
        "lambda",
        "response-loss",
        "report",
        "--endpoint-spec",
        str(endpoint_out),
        "--regression-report",
        str(regression_out),
        "--mitigation-acceptance",
        str(acceptance_out),
        "--hold-release",
        str(hold_out),
        "--out",
        str(report_out),
    )

    assert endpoint["live_mutation_call_performed"] is False
    assert set(endpoint["verified_operations"]) == {
        "launch_one_instance",
        "terminate_owned_instance",
    }
    assert fixture["no_real_lambda_call"] is True
    assert regression["regression_harness_passed"] is True
    assert acceptance["mitigation_accepted"] is True
    assert hold["hold_released_for_future_review"] is True
    assert report["future_launch_hold_released_for_review"] is True
    assert report["launch_allowed"] is False
