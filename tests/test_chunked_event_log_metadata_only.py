import json

from decodilo.syncer.event_log import EventLog, EventType
from decodilo.trainer.synthetic_large_state import SyntheticLargeStateSource


def test_large_synthetic_state_event_log_is_metadata_only(tmp_path) -> None:
    source = SyntheticLargeStateSource(
        run_id="run-large",
        learner_id="learner-0",
        seed=123,
        logical_parameter_count=536_870_912,
        bytes_per_parameter=2,
    )
    manifest = source.manifest()
    assert manifest.total_logical_bytes >= 1_073_741_824
    assert source.bytes_materialized == 0

    log = EventLog(tmp_path / "events.jsonl", run_id="run-large", truncate=True)
    log.append(
        EventType.LEARNER_FRAGMENT_SUBMITTED,
        logical_time=0,
        learner_id="learner-0",
        payload={
            "learner_id": "learner-0",
            "global_version_seen": 0,
            "tokens": 100,
            "storage_kind": "metadata_only",
            "payload_bytes": manifest.total_logical_bytes,
            "content_hash": manifest.manifest_hash,
            "manifest_hash": manifest.manifest_hash,
            "fragment_id": 0,
            "dtype": manifest.tensors[0].dtype,
            "shape": manifest.tensors[0].shape,
        },
    )

    text = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    event = json.loads(text)

    assert len(text.encode("utf-8")) < 5_000_000
    assert source.bytes_materialized == 0
    assert event["payload"]["payload_bytes"] == manifest.total_logical_bytes
    assert "data" not in event["payload"]
    assert "vector" not in event["payload"]
