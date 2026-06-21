import json
import subprocess
import sys

from decodilo.runtime.overhead_budget import OverheadBudget, check_overhead_budget
from decodilo.runtime.perf_characterization import PerformanceCharacterizationReport


def _minimal_report() -> PerformanceCharacterizationReport:
    return PerformanceCharacterizationReport(
        run_id="run-perf",
        profile_name="unit",
        config={"steps": 1},
        environment={"torch_available": False},
        trainer_type="numpy_convex",
        codec_modes={"fragment_artifact_codec": "binary_v1"},
        storage_modes={"payload_storage_mode": "chunked"},
        learner_count=1,
        fragment_count=1,
        chunk_size_bytes=1024,
        element_count=4,
        checkpoint_interval=1,
        logical_metrics={
            "useful_tokens_accepted": 10,
            "committed_sync_rounds": 1,
            "goodput_ratio": 1.0,
        },
        timing={"total_wall_time_seconds": 1.0},
        bytes={"artifact_bytes_written": 32},
        counters={},
        derived={"merge_time_fraction": 0.2},
        bottlenecks={"top_components_by_wall_time": [], "top_components_by_bytes": []},
        validation={
            "replay_passed": True,
            "metric_validation_passed": True,
            "artifact_audit_passed": True,
            "run_validate_passed": True,
            "preflight_passed": True,
        },
    )


def test_overhead_budget_passes_and_fails() -> None:
    report = _minimal_report()
    passed = check_overhead_budget(
        report=report,
        budget=OverheadBudget(max_merge_time_fraction=0.5),
    )
    failed = check_overhead_budget(
        report=report,
        budget=OverheadBudget(max_merge_time_fraction=0.01),
    )

    assert passed.passed is True
    assert failed.passed is False
    assert "merge_time_fraction" in failed.errors[0]


def test_overhead_budget_cli(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    budget_path = tmp_path / "budget.json"
    result_path = tmp_path / "budget_result.json"
    report_path.write_text(_minimal_report().to_json(), encoding="utf-8")
    budget_path.write_text(
        json.dumps({"max_merge_time_fraction": 0.5}, sort_keys=True),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "perf",
            "check-budget",
            "--report",
            str(report_path),
            "--budget-json",
            str(budget_path),
            "--out",
            str(result_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout)["passed"] is True
    assert json.loads(result_path.read_text(encoding="utf-8"))["passed"] is True
