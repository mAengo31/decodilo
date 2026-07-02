import numpy as np

from decodilo.syncer.event_log import EventLog
from decodilo.syncer.fragment_store import FragmentStore
from decodilo.syncer.outer_optimizer import create_outer_optimizer
from decodilo.syncer.quorum import PendingUpdate, QuorumPolicy, QuorumTracker


def test_sync_does_not_happen_below_quorum() -> None:
    tracker = QuorumTracker(QuorumPolicy(min_quorum=2))
    decision = tracker.decide(
        [PendingUpdate("a", global_version_seen=0, tokens=10, submitted_at=0)],
        current_version=0,
        current_tick=0,
    )

    assert not decision.should_commit
    assert decision.reason == "below_quorum"


def test_sync_happens_when_quorum_is_reached() -> None:
    tracker = QuorumTracker(QuorumPolicy(min_quorum=2))
    decision = tracker.decide(
        [
            PendingUpdate("a", global_version_seen=0, tokens=10, submitted_at=0),
            PendingUpdate("b", global_version_seen=0, tokens=10, submitted_at=0),
        ],
        current_version=0,
        current_tick=0,
    )

    assert decision.should_commit
    assert decision.accepted_learner_ids == ["a", "b"]


def test_late_learners_can_be_included_within_grace_window() -> None:
    tracker = QuorumTracker(QuorumPolicy(min_quorum=2, grace_window_ticks=2))
    pending = [
        PendingUpdate("a", global_version_seen=0, tokens=10, submitted_at=0),
        PendingUpdate("b", global_version_seen=0, tokens=10, submitted_at=1),
    ]
    first = tracker.decide(pending, current_version=0, current_tick=1)
    assert not first.should_commit

    pending.append(PendingUpdate("c", global_version_seen=0, tokens=10, submitted_at=2))
    second = tracker.decide(pending, current_version=0, current_tick=3)
    assert second.should_commit
    assert second.accepted_learner_ids == ["a", "b", "c"]


def test_late_learners_outside_grace_window_are_excluded_from_committed_round() -> None:
    store = FragmentStore(
        initial_global_vector=np.array([0.0]),
        num_fragments=1,
        quorum_policy=QuorumPolicy(min_quorum=2, grace_window_ticks=1),
        event_log=EventLog(),
    )
    store.submit_learner_update(
        learner_id="a",
        vector=np.array([1.0]),
        global_version_seen=0,
        tokens=10,
        submitted_at=0,
    )
    store.submit_learner_update(
        learner_id="b",
        vector=np.array([3.0]),
        global_version_seen=0,
        tokens=10,
        submitted_at=0,
    )
    assert store.maybe_commit(current_tick=0) is None
    commit = store.maybe_commit(current_tick=1)
    assert commit is not None
    assert commit.accepted_learner_ids == ["a", "b"]

    store.submit_learner_update(
        learner_id="c",
        vector=np.array([100.0]),
        global_version_seen=0,
        tokens=10,
        submitted_at=2,
    )
    assert "c" in store.pending


def test_failed_learners_do_not_block_progress() -> None:
    tracker = QuorumTracker(QuorumPolicy(min_quorum=2))
    decision = tracker.decide(
        [
            PendingUpdate("a", global_version_seen=0, tokens=10, submitted_at=0),
            PendingUpdate("b", global_version_seen=0, tokens=10, submitted_at=0),
            PendingUpdate("failed", global_version_seen=0, tokens=10, submitted_at=0),
        ],
        current_version=0,
        current_tick=0,
        failed_learner_ids={"failed"},
    )

    assert decision.should_commit
    assert decision.accepted_learner_ids == ["a", "b"]
    assert decision.rejected_learner_ids == {"failed": "failed"}



def test_chunked_commit_writer_failure_does_not_orphan_started_round() -> None:
    event_log = EventLog()

    def failing_writer(_role, _vector, _version):
        raise RuntimeError("artifact writer unavailable")

    store = FragmentStore(
        initial_global_vector=np.array([0.0]),
        num_fragments=1,
        quorum_policy=QuorumPolicy(min_quorum=1),
        optimizer=create_outer_optimizer("nesterov", outer_lr=0.5, momentum=0.9),
        event_log=event_log,
        event_payload_mode="chunked",
        merge_mode="streaming_chunked",
        global_vector_artifact_writer=failing_writer,
    )
    store.submit_learner_update(
        learner_id="a",
        vector=np.array([1.0]),
        global_version_seen=0,
        tokens=10,
        submitted_at=0,
    )

    try:
        store.maybe_commit(current_tick=1)
    except RuntimeError as exc:
        assert str(exc) == "artifact writer unavailable"
    else:  # pragma: no cover - test must fail if no exception is raised
        raise AssertionError("commit unexpectedly succeeded")

    assert store.global_version == 0
    assert getattr(store.optimizer, "step", 0) == 0
    event_types = [event.event_type.value for event in event_log.events]
    assert "sync_round_started" not in event_types
    assert "sync_round_committed" not in event_types
