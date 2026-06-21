import json

from lambda_m050_helpers import write_m050_inputs

from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_cloud_still_disabled_m050(tmp_path):
    paths = write_m050_inputs(tmp_path)
    artifacts = [
        paths["scope"],
        paths["access"],
        paths["ssh"],
        paths["commands"],
        paths["install"],
        paths["training"],
        paths["evidence_schema"],
        paths["risk"],
        paths["authorization"],
        paths["runbook"],
        paths["m050"],
    ]

    for path in artifacts:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["launch_ready"] is False
        assert payload["launch_allowed"] is False
        assert payload["billable_action_performed"] is False
        assert payload["real_mutation_enabled"] is False


def test_preflight_loads_m050_report_but_keeps_launch_disabled(tmp_path):
    paths = write_m050_inputs(tmp_path)
    report = run_lambda_preflight(m050_report=paths["m050"])

    assert report.m050_remote_bootstrap_summary is not None
    assert (
        report.m050_remote_bootstrap_summary["m051_authorization_status"]
        == "authorized_for_future_m051_metadata_only_bootstrap_review"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.real_mutation_enabled is False
