import json
import subprocess
import sys

from decodilo.runtime.run_spec import RunSpec, load_run_spec, write_run_spec


def test_run_spec_round_trip_stable(tmp_path) -> None:
    spec = RunSpec(
        run_id="run-spec",
        seed=123,
        learners=2,
        steps=20,
        min_quorum=1,
        grace_window=0,
        max_staleness_versions=1,
        vector_dim=2,
        num_fragments=1,
        local_steps_per_sync=5,
    )
    path = tmp_path / "run_spec.json"
    write_run_spec(path, spec)

    assert load_run_spec(path) == spec
    assert spec.sha256() == load_run_spec(path).sha256()


def test_local_run_from_run_spec_writes_spec_hash(tmp_path) -> None:
    spec = RunSpec(
        run_id="run-spec-local",
        seed=123,
        learners=2,
        steps=30,
        min_quorum=1,
        grace_window=0,
        max_staleness_versions=1,
        vector_dim=2,
        num_fragments=1,
        local_steps_per_sync=5,
    )
    spec_path = tmp_path / "input_run_spec.json"
    write_run_spec(spec_path, spec)
    subprocess.run(
        [sys.executable, "-m", "decodilo.cli", "local", "run", "--run-spec", str(spec_path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["run_id"] == "run-spec-local"
    assert report["run_spec_sha256"]
    assert report["metric_validation"]["passed"] is True
