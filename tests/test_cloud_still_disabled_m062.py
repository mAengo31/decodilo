from __future__ import annotations

from lambda_m062_helpers import write_m062_chain

from decodilo.lambda_cloud.m062_report import load_lambda_m062_report
from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_m062_preflight_integration_keeps_launch_disabled(tmp_path):
    paths = write_m062_chain(tmp_path)
    report = load_lambda_m062_report(paths["m062_report"])

    preflight = run_lambda_preflight(
        launch_plan=None,
        teardown_plan=None,
        ledger=None,
        m062_report=report,
    )

    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False
    assert preflight.m062_whoami_gpu_visibility_summary is not None
    assert preflight.m062_whoami_gpu_visibility_summary["report_passed"] is True
