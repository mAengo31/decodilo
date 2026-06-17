import pytest

from decodilo.runtime.checkpoint_lifecycle import (
    CheckpointLifecyclePolicy,
    plan_checkpoint_lifecycle,
)

pytestmark = pytest.mark.unit


def test_keep_latest_checkpoint_count_and_recovery_pointer() -> None:
    report = plan_checkpoint_lifecycle(
        syncer_checkpoints=[
            "syncer_checkpoint_0001.json",
            "syncer_checkpoint_0002.json",
            "syncer_checkpoint_0003.json",
        ],
        learner_checkpoints=["learner-0.checkpoint.json"],
        policy=CheckpointLifecyclePolicy(
            keep_latest_n_syncer_checkpoints=1,
            keep_latest_n_learner_checkpoints=1,
        ),
    )

    assert report.latest_recovery_checkpoint == "syncer_checkpoint_0003.json"
    assert report.checkpoints_retained == 2
    assert report.checkpoints_gc_eligible == 2

