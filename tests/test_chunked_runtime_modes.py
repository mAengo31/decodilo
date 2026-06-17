import subprocess
import sys

from decodilo.errors import InvariantViolation
from decodilo.runtime.chunked_runtime_modes import (
    should_use_chunked_payload,
    validate_runtime_modes,
)
from decodilo.runtime.run_spec import RunSpec, load_run_spec, write_run_spec


def test_run_spec_round_trips_chunked_storage_modes(tmp_path) -> None:
    spec = RunSpec(
        run_id="run-modes",
        seed=123,
        learners=2,
        steps=10,
        min_quorum=1,
        grace_window=0,
        max_staleness_versions=1,
        vector_dim=4,
        num_fragments=1,
        local_steps_per_sync=5,
        payload_storage_mode="chunked",
        checkpoint_storage_mode="dual",
        merge_mode="streaming_chunked",
        global_update_storage_mode="auto",
        chunk_store_root="chunks",
        artifact_root="artifacts",
        inline_payload_max_bytes=1024,
        chunk_size_bytes=4096,
        require_chunked_for_large_state=True,
    )
    path = tmp_path / "run_spec.json"
    write_run_spec(path, spec)

    loaded = load_run_spec(path)

    assert loaded.payload_storage_mode == "chunked"
    assert loaded.checkpoint_storage_mode == "dual"
    assert loaded.merge_mode == "streaming_chunked"
    assert loaded.global_update_storage_mode == "auto"
    assert loaded.stable_json() == spec.stable_json()


def test_runtime_mode_validation_and_auto_threshold() -> None:
    validate_runtime_modes(
        payload_storage_mode="chunked",
        checkpoint_storage_mode="chunked",
        merge_mode="streaming_chunked",
        global_update_storage_mode="chunked",
    )

    try:
        validate_runtime_modes(
            payload_storage_mode="inline",
            checkpoint_storage_mode="inline",
            merge_mode="streaming_chunked",
            global_update_storage_mode="inline",
        )
    except InvariantViolation as exc:
        assert "streaming_chunked" in str(exc)
    else:  # pragma: no cover - defensive branch
        raise AssertionError("invalid mode combination was accepted")

    assert should_use_chunked_payload(
        mode="auto",
        payload_bytes=2048,
        inline_payload_max_bytes=1024,
    )
    assert not should_use_chunked_payload(
        mode="auto",
        payload_bytes=512,
        inline_payload_max_bytes=1024,
    )


def test_cli_rejects_invalid_chunked_mode_combination(tmp_path) -> None:
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
            "1",
            "--min-quorum",
            "1",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(tmp_path / "report.json"),
            "--payload-storage-mode",
            "inline",
            "--merge-mode",
            "streaming_chunked",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert completed.returncode != 0
    assert "streaming_chunked" in completed.stderr
