import json

import pytest
from m010_binary_helpers import run_binary_local

from decodilo.errors import ReplayMismatchError
from decodilo.syncer.replay import replay_event_log

pytestmark = [pytest.mark.integration, pytest.mark.runtime, pytest.mark.replay]


def test_binary_replay_fails_when_referenced_artifact_is_corrupted(tmp_path) -> None:
    run_binary_local(tmp_path)
    first_submission = next(
        json.loads(line)
        for line in (tmp_path / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if '"event_type":"learner_fragment_submitted"' in line
    )
    manifest_path = tmp_path / first_submission["payload"]["artifact_ref"]["manifest_path"]
    manifest_path.write_text(
        manifest_path.read_text(encoding="utf-8").replace('"manifest_hash"', '"bad"', 1),
        encoding="utf-8",
    )

    with pytest.raises(ReplayMismatchError):
        replay_event_log(tmp_path / "events.jsonl")
