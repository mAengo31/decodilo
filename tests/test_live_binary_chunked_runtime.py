import pytest
from m010_binary_helpers import run_binary_local

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def test_live_binary_chunked_runtime_commits_replays_and_logs_metadata_only(tmp_path) -> None:
    report = run_binary_local(tmp_path)
    event_text = (tmp_path / "events.jsonl").read_text(encoding="utf-8")

    assert report["replay_validation"]["replay_passed"] is True
    assert report["metric_validation"]["passed"] is True
    assert report["metrics"]["chunked_fragment_submissions"] > 0
    assert report["metrics"]["binary_streaming_merges"] > 0
    assert report["metrics"]["merge_algorithm"] == "out_of_core_binary_v1"
    assert report["metrics"]["merge_blocks_processed"] > 0
    assert report["metrics"]["merge_peak_working_bytes_estimate"] > 0
    assert "tensor_binary_v1" in event_text
    assert '"data": [' not in event_text
    assert '"vector": [' not in event_text


def test_binary_global_update_delivery_metrics_and_ack(tmp_path) -> None:
    report = run_binary_local(tmp_path)

    assert (
        report["metrics"]["global_update_messages_sent"]
        >= report["metrics"]["global_update_acks"]
    )
    assert report["metrics"]["binary_global_update_messages_sent"] > 0
    assert report["metrics"]["binary_global_update_bytes_sent"] > 0
    assert report["metrics"]["binary_global_update_apply_failures"] == 0


def test_binary_chunked_checkpoint_recovery_is_primary(tmp_path) -> None:
    report = run_binary_local(tmp_path, restart=True)
    events = (tmp_path / "events.jsonl").read_text(encoding="utf-8")

    assert report["recovery_source"] == "chunked"
    assert report["replay_validation"]["replay_passed"] is True
    assert "syncer_recovered" in events
    assert "checkpoint_artifact_codec" in events
    assert not (tmp_path / "syncer_checkpoint.json").exists()
