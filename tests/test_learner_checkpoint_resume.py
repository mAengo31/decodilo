import json

import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.learner_checkpoint import (
    load_checkpoint,
    make_checkpoint,
    write_checkpoint_atomic,
)


def test_learner_checkpoint_round_trip_and_atomic_write(tmp_path) -> None:
    path = tmp_path / "learner-0.checkpoint.json"
    checkpoint = make_checkpoint(
        run_id="run-checkpoint",
        learner_id="learner-0",
        local_step=12,
        tokens_processed=1200,
        tokens_since_last_sync=300,
        last_global_version_seen=2,
        last_applied_global_version=2,
        throughput_tokens_per_step=100,
        parameter_vector=[1.0, 2.0],
        written_logical_time=12,
    )

    write_checkpoint_atomic(path, checkpoint)
    loaded = load_checkpoint(path)

    assert loaded == checkpoint
    assert not (tmp_path / "learner-0.checkpoint.tmp").exists()


def test_corrupted_checkpoint_is_rejected(tmp_path) -> None:
    path = tmp_path / "checkpoint.json"
    checkpoint = make_checkpoint(
        run_id="run-checkpoint",
        learner_id="learner-0",
        local_step=1,
        tokens_processed=100,
        tokens_since_last_sync=100,
        last_global_version_seen=0,
        last_applied_global_version=0,
        throughput_tokens_per_step=100,
        parameter_vector=[0.0],
        written_logical_time=1,
    )
    write_checkpoint_atomic(path, checkpoint)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["tokens_processed"] = 999
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")

    with pytest.raises(InvariantViolation, match="checksum"):
        load_checkpoint(path)
