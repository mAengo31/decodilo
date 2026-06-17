import json

import pytest

from decodilo.errors import InvariantViolation
from decodilo.trainer.state_codec import (
    decode_fragment,
    decode_state,
    encode_fragment,
    encode_state,
    make_fragment,
    make_state,
)


def test_trainer_state_and_fragment_round_trip_stably() -> None:
    state = make_state(
        trainer_type="numpy_convex",
        run_id="run-codec",
        learner_id="learner-0",
        global_version=1,
        local_step=2,
        tokens_processed=20,
        tokens_since_last_sync=10,
        parameters=[1.0, 2.0],
    )
    fragment = make_fragment(
        trainer_type="numpy_convex",
        run_id="run-codec",
        learner_id="learner-0",
        fragment_id=0,
        global_version=1,
        data=[1.0, 2.0],
        tokens=10,
    )

    assert decode_state(encode_state(state)) == state
    assert decode_fragment(encode_fragment(fragment)) == fragment
    assert encode_state(state) == encode_state(state)


def test_corrupted_checksum_and_wrong_version_are_rejected() -> None:
    state = make_state(
        trainer_type="numpy_convex",
        run_id="run-codec",
        learner_id="learner-0",
        global_version=1,
        local_step=2,
        tokens_processed=20,
        tokens_since_last_sync=10,
        parameters=[1.0, 2.0],
    )
    payload = json.loads(encode_state(state))
    payload["tokens_processed"] = 999

    with pytest.raises(InvariantViolation, match="checksum"):
        decode_state(json.dumps(payload))

    payload = json.loads(encode_state(state))
    payload["codec_version"] = "v2"
    payload["checksum"] = "not-recomputed"
    with pytest.raises(InvariantViolation):
        decode_state(json.dumps(payload))
