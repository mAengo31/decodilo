"""Deterministic chaos events for logical simulation time."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from decodilo.learner.fake_learner import FakeLearner
from decodilo.syncer.event_log import EventLog, EventType


class ChaosAction(str, Enum):
    PAUSE_LEARNER = "pause_learner"
    FAIL_LEARNER = "fail_learner"
    RECOVER_LEARNER = "recover_learner"
    SLOW_LEARNER = "slow_learner"
    RESTORE_LEARNER_SPEED = "restore_learner_speed"


@dataclass(frozen=True)
class ChaosEvent:
    tick: int
    action: ChaosAction
    learner_id: str
    factor: float | None = None


class ChaosPlan:
    """A deterministic map from logical ticks to learner state transitions."""

    def __init__(self, events: list[ChaosEvent] | None = None) -> None:
        self.events_by_tick: dict[int, list[ChaosEvent]] = {}
        for event in events or []:
            if event.tick < 0:
                raise ValueError("chaos event tick must be non-negative")
            self.events_by_tick.setdefault(event.tick, []).append(event)

    def apply(
        self,
        *,
        tick: int,
        learners: dict[str, FakeLearner],
        event_log: EventLog,
        current_global_version: int,
    ) -> None:
        for event in self.events_by_tick.get(tick, []):
            learner = learners[event.learner_id]
            if event.action == ChaosAction.PAUSE_LEARNER:
                learner.pause()
                event_log.append(
                    EventType.LEARNER_PAUSED,
                    logical_time=tick,
                    learner_id=event.learner_id,
                    payload={"learner_id": event.learner_id},
                )
            elif event.action == ChaosAction.FAIL_LEARNER:
                learner.fail()
                event_log.append(
                    EventType.LEARNER_FAILED,
                    logical_time=tick,
                    learner_id=event.learner_id,
                    payload={"learner_id": event.learner_id},
                )
            elif event.action == ChaosAction.RECOVER_LEARNER:
                learner.recover(recovery_version=current_global_version)
                event_log.append(
                    EventType.LEARNER_RECOVERED,
                    logical_time=tick,
                    learner_id=event.learner_id,
                    payload={
                        "learner_id": event.learner_id,
                        "recovery_version": current_global_version,
                    },
                )
            elif event.action == ChaosAction.SLOW_LEARNER:
                learner.slow(event.factor or 0.5)
            elif event.action == ChaosAction.RESTORE_LEARNER_SPEED:
                learner.restore_speed()
