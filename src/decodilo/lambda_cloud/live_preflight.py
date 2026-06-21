"""Live read-only Lambda preflight wrapper."""

from __future__ import annotations

from pathlib import Path

from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.live_resource_ledger import load_lambda_live_ledger_report
from decodilo.lambda_cloud.preflight import LambdaPreflightReport, run_lambda_preflight
from decodilo.lambda_cloud.read_only_audit import load_lambda_read_only_audit_report


def run_lambda_live_preflight(
    *,
    discovery_report: str | Path,
    read_only_audit: str | Path,
    ledger: str | Path,
    launch_plan: str | Path,
    teardown_plan: str | Path,
    m020_report: str | Path | None = None,
) -> LambdaPreflightReport:
    discovery = load_lambda_live_discovery_report(discovery_report)
    audit = load_lambda_read_only_audit_report(read_only_audit)
    live_ledger = load_lambda_live_ledger_report(ledger)
    report = run_lambda_preflight(
        launch_plan=launch_plan,
        teardown_plan=teardown_plan,
        live_discovery_report=discovery,
        read_only_audit=audit,
        live_ledger=live_ledger,
        m020_report=m020_report,
    )
    return report
