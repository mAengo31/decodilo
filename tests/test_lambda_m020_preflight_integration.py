from test_lambda_m020_report import _write_m020_inputs

from decodilo.lambda_cloud.m020_report import build_lambda_m020_report, write_lambda_m020_report
from decodilo.lambda_cloud.preflight import run_lambda_preflight


def test_lambda_preflight_includes_m020_report_status(tmp_path) -> None:
    inputs = _write_m020_inputs(tmp_path, with_approval=True)
    report = build_lambda_m020_report(
        discovery_report=inputs[0],
        read_only_audit=inputs[1],
        ledger=inputs[2],
        launch_plan=inputs[3],
        teardown_plan=inputs[4],
        price_snapshot=inputs[5],
        credits=100,
        max_run_budget=50,
        planned_hours=0.5,
        safety_buffer_percentage=15,
        approval_manifest=inputs[6],
    )
    m020_path = tmp_path / "m020.json"
    write_lambda_m020_report(m020_path, report)

    preflight = run_lambda_preflight(
        live_discovery_report=inputs[0],
        read_only_audit=inputs[1],
        live_ledger=inputs[2],
        launch_plan=inputs[3],
        teardown_plan=inputs[4],
        m020_report=m020_path,
    )

    assert preflight.m020_readiness_summary is not None
    assert preflight.m020_readiness_summary["future_fake_launch_lifecycle_candidate"] is True
    assert preflight.m020_readiness_summary["future_real_launch_candidate"] is False
    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False


def test_lambda_preflight_warns_when_m020_report_missing(tmp_path) -> None:
    inputs = _write_m020_inputs(tmp_path)

    preflight = run_lambda_preflight(
        live_discovery_report=inputs[0],
        read_only_audit=inputs[1],
        live_ledger=inputs[2],
        launch_plan=inputs[3],
        teardown_plan=inputs[4],
    )

    assert preflight.m020_readiness_summary is None
    assert "M020 Lambda readiness report missing" in preflight.warnings
    assert preflight.launch_allowed is False
