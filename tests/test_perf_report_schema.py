import pytest

from decodilo.runtime.local_runner import LocalRunConfig
from decodilo.runtime.perf_harness import run_local_overhead_harness


@pytest.mark.perf
def test_perf_report_schema_contains_binary_codec_and_nonnegative_sections(tmp_path) -> None:
    report = run_local_overhead_harness(
        config=LocalRunConfig(
            learners=2,
            steps=30,
            min_quorum=1,
            seed=123,
            workdir=tmp_path / "run",
            report_json=tmp_path / "run" / "report.json",
            payload_storage_mode="chunked",
            global_update_storage_mode="chunked",
            checkpoint_storage_mode="chunked",
            merge_mode="streaming_chunked",
            tensor_artifact_codec="binary_v1",
            fragment_artifact_codec="binary_v1",
            checkpoint_artifact_codec="binary_v1",
            allow_spill_to_disk=True,
        ),
        out=tmp_path / "perf.json",
    )
    payload = report.model_dump(mode="json")

    assert payload["codec_modes"]["tensor_artifact_codec"] == "binary_v1"
    assert payload["validation"]["replay_passed"] is True
    assert payload["validation"]["metric_validation_passed"] is True
    for section in ("overhead_breakdown", "derived_ratios"):
        for value in payload[section].values():
            assert value >= 0
