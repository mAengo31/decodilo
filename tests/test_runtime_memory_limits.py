import json
import subprocess
import sys

import pytest

from decodilo.runtime.learner_checkpoint import load_chunked_learner_checkpoint
from decodilo.runtime.resource_limits import RuntimeResourceLimits
from decodilo.runtime.syncer_checkpoint import load_chunked_syncer_checkpoint


def test_runtime_resource_limits_convert_from_mb(tmp_path) -> None:
    limits = RuntimeResourceLimits.from_mb(
        memory_budget_mb=1,
        spill_dir=tmp_path / "spill",
        allow_spill_to_disk=True,
        max_spill_mb=2,
        chunked_checkpoints=True,
    )

    assert limits.max_in_memory_fragment_bytes == 1024 * 1024
    assert limits.max_spill_bytes == 2 * 1024 * 1024
    assert limits.to_memory_budget().allow_spill_to_disk is True


@pytest.mark.integration
def test_local_run_accepts_memory_limit_and_chunked_checkpoint_flags(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "1",
            "--steps",
            "5",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(tmp_path / "report.json"),
            "--memory-budget-mb",
            "1",
            "--allow-spill-to-disk",
            "--spill-dir",
            str(tmp_path / "spill"),
            "--max-spill-mb",
            "2",
            "--chunked-checkpoints",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert json.loads(completed.stdout)["metric_validation_passed"] is True
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["perf_counters"]["wall_time_seconds"] >= 0
    assert list((tmp_path / "chunked_checkpoints").glob("*.artifact.json"))
    assert not (tmp_path / "spill").exists()

    checkpoint_store = tmp_path / "chunked_checkpoints" / "store"
    learner_manifest = next((tmp_path / "chunked_checkpoints").glob("learner-*.artifact.json"))
    syncer_manifest = tmp_path / "chunked_checkpoints" / "syncer_checkpoint.artifact.json"
    assert load_chunked_learner_checkpoint(
        manifest_path=learner_manifest,
        chunk_store_dir=checkpoint_store,
    ).run_id == report["run_id"]
    assert load_chunked_syncer_checkpoint(
        manifest_path=syncer_manifest,
        chunk_store_dir=checkpoint_store,
    ).run_id == report["run_id"]
