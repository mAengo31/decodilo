import json

import numpy as np

from decodilo.sim.chaos import ChaosAction, ChaosEvent, ChaosPlan
from decodilo.sim.runner import SimulationConfig, run_simulation
from decodilo.syncer.event_log import EventLog
from decodilo.syncer.fragment_store import FragmentStore
from decodilo.syncer.quorum import QuorumPolicy


def _events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_one_learner_fails_permanently_quorum_still_met(tmp_path) -> None:
    log_path = tmp_path / "events.jsonl"
    result = run_simulation(
        SimulationConfig(learners=4, vector_dim=4, steps=60, local_steps_per_sync=5, min_quorum=2),
        chaos_plan=ChaosPlan(
            [ChaosEvent(tick=3, action=ChaosAction.FAIL_LEARNER, learner_id="learner-0")]
        ),
        event_log_path=log_path,
    )

    assert result.metrics.committed_sync_rounds > 0
    assert result.metrics.learner_failed_ticks["learner-0"] > 0
    assert result.final_global_version > 0
    learner_zero_events = [
        event for event in _events(log_path) if event.get("learner_id") == "learner-0"
    ]
    failure_time = next(
        event["logical_time"]
        for event in learner_zero_events
        if event["event_type"] == "learner_failed"
    )
    assert not [
        event
        for event in learner_zero_events
        if event["event_type"] == "learner_fragment_submitted"
        and event["logical_time"] > failure_time
    ]


def test_very_slow_learner_is_often_excluded_when_grace_is_zero(tmp_path) -> None:
    log_path = tmp_path / "slow-events.jsonl"
    result = run_simulation(
        SimulationConfig(
            learners=4,
            vector_dim=4,
            steps=90,
            local_steps_per_sync=3,
            min_quorum=2,
            max_staleness_versions=0,
        ),
        chaos_plan=ChaosPlan(
            [
                ChaosEvent(
                    tick=0,
                    action=ChaosAction.SLOW_LEARNER,
                    learner_id="learner-0",
                    factor=0.1,
                )
            ]
        ),
        event_log_path=log_path,
    )
    committed = [
        event
        for event in _events(log_path)
        if event["event_type"] == "sync_round_committed"
    ]
    missing_slow = [
        event
        for event in committed
        if "learner-0" not in event["payload"]["accepted_learner_ids"]
    ]

    assert result.metrics.committed_sync_rounds > 0
    assert missing_slow
    assert result.metrics.learner_uptime_ticks["learner-0"] == 90


def test_all_but_one_learner_fail_quorum_not_met() -> None:
    result = run_simulation(
        SimulationConfig(learners=4, vector_dim=4, steps=40, local_steps_per_sync=5, min_quorum=2),
        chaos_plan=ChaosPlan(
            [
                ChaosEvent(tick=0, action=ChaosAction.FAIL_LEARNER, learner_id="learner-0"),
                ChaosEvent(tick=0, action=ChaosAction.FAIL_LEARNER, learner_id="learner-1"),
                ChaosEvent(tick=0, action=ChaosAction.FAIL_LEARNER, learner_id="learner-2"),
            ]
        ),
    )

    assert result.metrics.committed_sync_rounds == 0
    assert result.final_global_version == 0
    assert result.metrics.skipped_sync_rounds > 0


def test_stale_learner_recovers_and_can_contribute_after_new_version(tmp_path) -> None:
    log_path = tmp_path / "events.jsonl"
    result = run_simulation(
        SimulationConfig(
            learners=4,
            vector_dim=4,
            steps=80,
            local_steps_per_sync=5,
            min_quorum=2,
            max_staleness_versions=0,
        ),
        chaos_plan=ChaosPlan(
            [
                ChaosEvent(tick=1, action=ChaosAction.FAIL_LEARNER, learner_id="learner-0"),
                ChaosEvent(tick=30, action=ChaosAction.RECOVER_LEARNER, learner_id="learner-0"),
            ]
        ),
        event_log_path=log_path,
    )
    records = _events(log_path)
    stale_rejection_index = next(
        index
        for index, event in enumerate(records)
        if event["event_type"] == "fragment_rejected"
        and event["learner_id"] == "learner-0"
        and event["payload"]["reason"] == "stale"
    )
    later_accepts = [
        event
        for event in records[stale_rejection_index + 1 :]
        if event["event_type"] == "sync_round_committed"
        and "learner-0" in event["payload"]["accepted_learner_ids"]
    ]

    assert result.metrics.stale_fragments > 0
    assert result.metrics.stale_tokens > 0
    assert later_accepts


def test_zero_token_fragment_is_rejected_and_has_no_numerical_effect() -> None:
    store = FragmentStore(
        initial_global_vector=np.array([1.0]),
        num_fragments=1,
        quorum_policy=QuorumPolicy(min_quorum=1),
        event_log=EventLog(run_id="zero-token-test"),
    )
    store.submit_learner_update(
        learner_id="zero",
        vector=np.array([100.0]),
        global_version_seen=0,
        tokens=0,
        submitted_at=0,
    )

    assert store.maybe_commit(current_tick=0) is None
    np.testing.assert_allclose(store.global_vector, np.array([1.0]))
    assert store.metrics.rejected_fragments == 1
    assert store.metrics.rejection_reasons == {"zero_tokens": 1}
