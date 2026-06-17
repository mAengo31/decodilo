import json

import numpy as np
import pytest

from decodilo.errors import ReplayMismatchError
from decodilo.sim.runner import SimulationConfig, run_simulation
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.replay import replay_event_log


def _run_log(tmp_path):
    log_path = tmp_path / "events.jsonl"
    result = run_simulation(
        SimulationConfig(
            learners=3,
            vector_dim=4,
            steps=30,
            local_steps_per_sync=5,
            min_quorum=2,
            seed=11,
        ),
        event_log_path=log_path,
    )
    return log_path, result


def _load_lines(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_lines(path, records) -> None:
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True, separators=(",", ":")) for record in records)
        + "\n",
        encoding="utf-8",
    )


def test_event_json_serialization_is_stable() -> None:
    log = EventLog(run_id="run-test")
    event = log.append(
        EventType.LEARNER_STARTED,
        logical_time=0,
        learner_id="learner-0",
        payload={"learner_id": "learner-0"},
    )

    assert event.to_json_line() == (
        '{"event_id":"run-test:00000000:learner_started","event_type":"learner_started",'
        '"fragment_id":null,"learner_id":"learner-0","logical_time":0,'
        '"payload":{"learner_id":"learner-0"},"round_id":null,"run_id":"run-test",'
        '"schema_version":"v1","sequence":0}'
    )


def test_replay_rejects_unknown_schema_version(tmp_path) -> None:
    log_path, _ = _run_log(tmp_path)
    records = _load_lines(log_path)
    records[0]["schema_version"] = "v2"
    tampered = tmp_path / "unknown-schema.jsonl"
    _write_lines(tampered, records)

    with pytest.raises(ReplayMismatchError):
        replay_event_log(tampered)


def test_replay_rejects_missing_required_event_fields(tmp_path) -> None:
    log_path, _ = _run_log(tmp_path)
    records = _load_lines(log_path)
    records[0].pop("run_id")
    tampered = tmp_path / "missing-field.jsonl"
    _write_lines(tampered, records)

    with pytest.raises(ReplayMismatchError):
        replay_event_log(tampered)


def test_replay_rejects_out_of_order_logical_time(tmp_path) -> None:
    log_path, _ = _run_log(tmp_path)
    records = _load_lines(log_path)
    for index in range(1, len(records)):
        if records[index - 1]["logical_time"] > 1:
            records[index]["logical_time"] = 0
            break
    tampered = tmp_path / "out-of-order.jsonl"
    _write_lines(tampered, records)

    with pytest.raises(ReplayMismatchError):
        replay_event_log(tampered)


def test_tampering_with_committed_vector_causes_replay_failure(tmp_path) -> None:
    log_path, _ = _run_log(tmp_path)
    records = _load_lines(log_path)
    for record in records:
        if record["event_type"] == "sync_round_committed":
            record["payload"]["new_global_vector"][0] += 1.0
            break
    tampered = tmp_path / "tampered-vector.jsonl"
    _write_lines(tampered, records)

    with pytest.raises(ReplayMismatchError):
        replay_event_log(tampered)


def test_removing_fragment_submission_causes_replay_failure(tmp_path) -> None:
    log_path, _ = _run_log(tmp_path)
    records = _load_lines(log_path)
    for index, record in enumerate(records):
        if record["event_type"] == "learner_fragment_submitted":
            del records[index]
            break
    tampered = tmp_path / "missing-submission.jsonl"
    _write_lines(tampered, records)

    with pytest.raises(ReplayMismatchError):
        replay_event_log(tampered)


def test_changing_accepted_token_count_causes_replay_failure(tmp_path) -> None:
    log_path, _ = _run_log(tmp_path)
    records = _load_lines(log_path)
    for record in records:
        if record["event_type"] == "sync_round_committed":
            record["payload"]["useful_tokens"] += 1
            break
    tampered = tmp_path / "bad-token-count.jsonl"
    _write_lines(tampered, records)

    with pytest.raises(ReplayMismatchError):
        replay_event_log(tampered)


def test_replaying_same_log_twice_returns_identical_state(tmp_path) -> None:
    log_path, result = _run_log(tmp_path)

    first = replay_event_log(log_path)
    second = replay_event_log(log_path)

    assert first.final_global_vector is not None
    assert second.final_global_vector is not None
    np.testing.assert_allclose(first.final_global_vector, result.final_global_vector)
    np.testing.assert_allclose(first.final_global_vector, second.final_global_vector)
    assert first.accepted_useful_tokens == second.accepted_useful_tokens
    assert first.sync_round_composition == second.sync_round_composition

