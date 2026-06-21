import json
import subprocess
import sys

import pytest

from decodilo.errors import BudgetExceededError, PricingAmbiguityError
from decodilo.pricing.budget import BudgetGuard, build_run_budget_manifest
from decodilo.pricing.freshness import require_usable_snapshot
from decodilo.pricing.registry import import_json_snapshot, query_snapshot_price
from decodilo.pricing.snapshots import write_price_snapshot


def test_budget_cli_rejects_sample_snapshot_by_default_and_prints_record_ids(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=True,
    )

    rejected = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "budget",
            "estimate",
            "--credits",
            "7500",
            "--gpu-type",
            "H100 SXM",
            "--gpus-per-instance",
            "8",
            "--instances",
            "1",
            "--hours",
            "10",
            "--price-snapshot",
            str(snapshot_path),
        ],
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "sample price snapshot" in rejected.stderr

    accepted = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "budget",
            "estimate",
            "--credits",
            "7500",
            "--gpu-type",
            "H100 SXM",
            "--gpus-per-instance",
            "8",
            "--instances",
            "1",
            "--hours",
            "10",
            "--price-snapshot",
            str(snapshot_path),
            "--allow-sample-prices",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(accepted.stdout)
    assert payload["snapshot_id"] == snapshot.snapshot_id
    assert payload["record_id"]
    assert payload["base_estimated_cost"] == 199.20000000000002
    assert payload["budget_manifest"]["price_snapshot_id"] == snapshot.snapshot_id


def test_fresh_manual_snapshot_manifest_is_accepted_and_over_budget_rejected(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    require_usable_snapshot(snapshot)
    record = query_snapshot_price(snapshot, gpu_type="H100 SXM", gpus_per_instance=8)
    manifest = build_run_budget_manifest(
        run_id="run-budget",
        provider="lambda",
        mode="cloud-dry-run",
        price_snapshot_id=snapshot.snapshot_id,
        selected_price_record_ids=[record.record_id],
        planned_instances=1,
        gpus_per_instance=8,
        planned_hours=10,
        base_estimated_cost=199.2,
        safety_buffer_percentage=0.15,
        safety_buffer_adjusted_cost=229.08,
        max_run_budget=7500,
        starting_credits=7500,
        projected_remaining_credits=7270.92,
    )

    assert manifest.estimated_gpu_hours == 80
    with pytest.raises(BudgetExceededError):
        BudgetGuard(starting_credits=100).require_run_allowed(
            estimated_run_cost=199.2,
            max_run_budget=100,
        )


def test_stale_snapshot_budget_use_is_rejected_by_default(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    snapshot = import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=False,
    )
    stale = snapshot.model_copy(update={"captured_at_utc": "2026-01-01T00:00:00Z"})
    write_price_snapshot(snapshot_path, stale)

    with pytest.raises(PricingAmbiguityError, match="stale"):
        require_usable_snapshot(stale)


@pytest.mark.integration
def test_local_run_report_includes_budget_manifest_when_pricing_supplied(tmp_path) -> None:
    snapshot_path = tmp_path / "snapshot.json"
    import_json_snapshot(
        provider="lambda",
        input_path="tests/fixtures/lambda_prices_expected.json",
        output_path=snapshot_path,
        is_sample_data=True,
    )
    report_path = tmp_path / "report.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "2",
            "--steps",
            "30",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--price-snapshot",
            str(snapshot_path),
            "--allow-sample-prices",
            "--credits",
            "7500",
            "--gpu-type",
            "H100 SXM",
            "--gpus-per-instance",
            "8",
            "--instances",
            "1",
            "--hours",
            "1",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["budget_manifest"]["mode"] == "local"
    assert report["budget_manifest"]["planned_gpus"] == 8
    assert report["budget_manifest"]["allow_sample_prices"] is True
