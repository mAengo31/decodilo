from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lambda_m047_helpers import SUCCESS_REGION, SUCCESS_SHAPE, write_m047_inputs

from decodilo.lambda_cloud.m047_report import build_lambda_m047_report_from_paths


def test_m047_report_summarizes_successful_lifecycle_smoke(tmp_path):
    paths = write_m047_inputs(tmp_path)

    report = build_lambda_m047_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        live_region_selection=paths["region_selection"],
        evidence_package=paths["evidence"],
        live_parser=paths["parsed_instance_types"],
        alias_resolution=paths["alias"],
        price_join=paths["price_join"],
        strategy_update=paths["strategy"],
    )

    assert report.report_passed is True
    assert report.success_record_status == "lifecycle_smoke_success"
    assert report.reconciliation_status == "passed"
    assert report.evidence_package_status == "complete"
    assert report.live_parser_status == "parsed"
    assert report.live_region_selection == SUCCESS_REGION
    assert report.alias_resolution_status == "alias_matched"
    assert report.price_join_status == "matched"
    assert report.selected_candidate == SUCCESS_SHAPE
    assert report.historical_billable_action_performed is True
    assert report.billable_action_performed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m047_report_cli_writes_disabled_report(tmp_path):
    paths = write_m047_inputs(tmp_path / "artifacts")
    out = tmp_path / "cli-m047.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "m047",
            "report",
            "--success-record",
            str(paths["success"]),
            "--reconciliation",
            str(paths["reconciliation"]),
            "--closeout",
            str(paths["closeout"]),
            "--live-region-selection",
            str(paths["region_selection"]),
            "--evidence-package",
            str(paths["evidence"]),
            "--live-parser",
            str(paths["parsed_instance_types"]),
            "--alias-resolution",
            str(paths["alias"]),
            "--price-join",
            str(paths["price_join"]),
            "--strategy-update",
            str(paths["strategy"]),
            "--out",
            str(out),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["report_passed"] is True
    assert payload["launch_ready"] is False
    assert payload["launch_allowed"] is False
