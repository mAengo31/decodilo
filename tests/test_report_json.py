import json
import subprocess
import sys

from decodilo.sim.runner import SimulationConfig, run_simulation


def test_simulate_report_json_schema(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    result = run_simulation(
        SimulationConfig(learners=4, vector_dim=4, steps=20, min_quorum=2, seed=123)
    )
    result.write_report_json(report_path)

    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["run_id"] == result.run_id
    assert report["code_version"] == "0.1.0"
    assert report["final_global_version"] == result.final_global_version
    assert report["final_loss"] == result.final_loss
    assert report["pricing_assumptions"] is None
    assert report["config"]["learners"] == 4
    assert report["metrics"]["total_tokens_processed"] == result.metrics.total_tokens_processed
    assert "goodput_ratio" in report["metrics"]


def test_simulate_cli_writes_report_json(tmp_path) -> None:
    report_path = tmp_path / "cli-report.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "simulate",
            "--learners",
            "4",
            "--steps",
            "20",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--report-json",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["config"]["learners"] == 4
    assert report["config"]["steps"] == 20
    assert report["final_global_version"] > 0
    assert report["metrics"]["committed_sync_rounds"] > 0
