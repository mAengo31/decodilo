from __future__ import annotations

from types import SimpleNamespace

from decodilo.runtime.learner_worker import LearnerWorker


class _DummyTrainer:
    def __init__(self) -> None:
        self.global_version = 0
        self.accepted = 0

    def health(self) -> SimpleNamespace:
        return SimpleNamespace(global_version=self.global_version)

    def mark_update_accepted(self) -> None:
        self.accepted += 1


def test_learner_clears_inflight_fragment_when_new_global_version_arrives() -> None:
    trainer = _DummyTrainer()
    worker = LearnerWorker.__new__(LearnerWorker)
    worker.learner_id = "learner-0"
    worker.trainer = trainer
    worker.in_flight_idempotency_key = "run:learner-0:step-1:v-0"
    worker.artifact_transport = None

    def apply_global_vector(_vector, *, global_version: int) -> None:
        trainer.global_version = global_version

    worker._apply_global_vector = apply_global_vector

    worker._handle_global_payload(
        {
            "global_version": 1,
            "global_vector": [0.1, 0.2],
        }
    )

    assert trainer.global_version == 1
    assert worker.in_flight_idempotency_key is None



def test_learner_clears_inflight_fragment_from_immediate_commit_payload() -> None:
    trainer = _DummyTrainer()
    worker = LearnerWorker.__new__(LearnerWorker)
    worker.learner_id = "learner-0"
    worker.trainer = trainer
    worker.in_flight_idempotency_key = "run:learner-0:step-1:v-0"
    worker.artifact_transport = None

    worker._handle_global_payload(
        {
            "commit": {"accepted_learner_ids": ["learner-0", "learner-1"]},
        }
    )

    assert worker.in_flight_idempotency_key is None
    assert trainer.accepted == 1


def test_learner_does_not_repeatedly_mark_same_commit_after_inflight_cleared() -> None:
    trainer = _DummyTrainer()
    worker = LearnerWorker.__new__(LearnerWorker)
    worker.learner_id = "learner-0"
    worker.trainer = trainer
    worker.in_flight_idempotency_key = None
    worker.artifact_transport = None

    worker._handle_global_payload(
        {
            "last_commit": {"accepted_learner_ids": ["learner-0", "learner-1"]},
        }
    )

    assert trainer.accepted == 0
    assert worker.in_flight_idempotency_key is None
