import json
import subprocess
import sys

import pytest

from decodilo.runtime.perf_characterization import (
    PerformanceCharacterizationReport,
    environment_summary,
)


def _minimal_report() -> PerformanceCharacterizationReport:
    return PerformanceCharacterizationReport(
        run_id="run-perf",
        profile_name="unit",
        config={"steps": 1},
        environment=environment_summary(),
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
        timing={
            "total_wall_time_seconds": 1.0,
            "train_wall_time_seconds": 0.2,
            "fragment_encode_wall_time_seconds": 0.1,
            "artifact_write_wall_time_seconds": 0.1,
            "artifact_read_wall_time_seconds": 0.1,
            "merge_wall_time_seconds": 0.2,
            "global_update_decode_apply_wall_time_seconds": 0.1,
            "checkpoint_write_wall_time_seconds": 0.1,
            "checkpoint_restore_wall_time_seconds": None,
            "replay_wall_time_seconds": 0.1,
            "run_validate_wall_time_seconds": None,
            "gc_plan_wall_time_seconds": None,
            "preflight_wall_time_seconds": None,
        },
        bytes={
            "tensor_bytes_encoded": 32,
            "artifact_bytes_written": 32,
            "artifact_bytes_read": 32,
            "merge_input_bytes": 32,
            "merge_output_bytes": 32,
            "checkpoint_bytes_written": None,
            "replay_artifact_bytes_read": None,
        },
        counters={
            "artifact_write_count": 1,
            "artifact_read_count": 1,
            "merge_blocks_processed": 1,
            "checkpoints_written": 1,
            "event_segments_written": 0,
            "replay_events_read": None,
            "replay_segments_read": None,
        },
        derived={
            "useful_tokens_per_second": 10.0,
            "artifact_bytes_per_useful_token": 3.2,
            "train_time_fraction": 0.2,
            "encode_time_fraction": 0.1,
            "artifact_io_time_fraction": 0.2,
            "merge_time_fraction": 0.2,
            "checkpoint_time_fraction": 0.1,
            "replay_time_fraction": 0.1,
            "lifecycle_validation_time_fraction": None,
        },
        bottlenecks={
            "top_components_by_wall_time": [{"component": "merge", "value": 0.2}],
            "top_components_by_bytes": [{"component": "artifact_bytes_read", "value": 32.0}],
            "warnings": [],
        },
        validation={
            "replay_passed": True,
            "metric_validation_passed": True,
            "artifact_audit_passed": True,
            "run_validate_passed": True,
            "preflight_passed": True,
        },
    )


def test_performance_characterization_report_schema_and_ratios() -> None:
    report = _minimal_report()
    payload = report.model_dump(mode="json")

    assert payload["cloud_state"] == {"launch_ready": False, "launch_allowed": False}
    for key, value in payload["derived"].items():
        if key.endswith("_fraction") and value is not None:
            assert 0.0 <= value <= 1.0
    assert payload["timing"]["checkpoint_restore_wall_time_seconds"] is None


@pytest.mark.perf
@pytest.mark.integration
def test_perf_characterize_cli_writes_report(tmp_path) -> None:
    out = tmp_path / "perf_characterization.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "perf",
            "characterize",
            "--workdir",
            str(tmp_path / "run"),
            "--out",
            str(out),
            "--learners",
            "1",
            "--steps",
            "20",
            "--min-quorum",
            "1",
            "--vector-dim",
            "4",
            "--allow-spill-to-disk",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=40,
    )
    summary = json.loads(completed.stdout)
    report = json.loads(out.read_text(encoding="utf-8"))

    assert summary["replay_passed"] is True
    assert report["validation"]["metric_validation_passed"] is True
    assert report["cloud_state"]["launch_allowed"] is False

