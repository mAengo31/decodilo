"""Provider-agnostic dry-run helpers."""

from __future__ import annotations

from pathlib import Path

from decodilo.cloud.launch_plan import (
    CloudDryRunReport,
    load_cloud_dry_run_report,
    write_cloud_dry_run_report,
)
from decodilo.cloud.safety import validate_cloud_plan


def write_report(path: str | Path, report: CloudDryRunReport) -> None:
    write_cloud_dry_run_report(path, report)


def validate_report(path: str | Path) -> list[str]:
    report = load_cloud_dry_run_report(path)
    return [*report.validation_errors, *validate_cloud_plan(report.plan)]
