import subprocess
import sys

from decodilo.runtime.preflight import run_local_preflight
from decodilo.runtime.run_spec import RunSpec, write_run_spec


def test_local_preflight_passes_live_chunked_run(tmp_path) -> None:
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
            "20",
            "--min-quorum",
            "1",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(tmp_path / "report.json"),
            "--payload-storage-mode",
            "chunked",
            "--global-update-storage-mode",
            "chunked",
            "--checkpoint-storage-mode",
            "chunked",
            "--merge-mode",
            "streaming_chunked",
            "--chunk-size-mb",
            "1",
            "--memory-budget-mb",
            "1",
            "--allow-spill-to-disk",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=25,
    )

    result = run_local_preflight(workdir=tmp_path)

    assert result.preflight_passed is True
    assert result.launch_ready is False
    assert result.launch_allowed is False


def test_preflight_fails_large_expected_state_with_inline_only_modes(tmp_path) -> None:
    spec = RunSpec(
        run_id="run-large-inline",
        seed=123,
        learners=2,
        steps=10,
        min_quorum=1,
        grace_window=0,
        max_staleness_versions=1,
        vector_dim=4,
        num_fragments=1,
        local_steps_per_sync=5,
        trainer_config={"parameter_count": 700_000_000, "bytes_per_parameter": 2},
        payload_storage_mode="inline",
        global_update_storage_mode="inline",
        checkpoint_storage_mode="inline",
        merge_mode="in_memory",
        inline_payload_max_bytes=1024,
        require_chunked_for_large_state=True,
    )
    write_run_spec(tmp_path / "run_spec.json", spec)

    result = run_local_preflight(workdir=tmp_path)

    assert result.preflight_passed is False
    assert any("payload storage" in error for error in result.errors)
    assert any("global updates" in error for error in result.errors)
    assert any("checkpoints" in error for error in result.errors)
    assert any("streaming_chunked merge" in warning for warning in result.warnings)
