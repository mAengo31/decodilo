from __future__ import annotations

import asyncio
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

    asyncio.run(
        worker._handle_global_payload(
            {
                "global_version": 1,
                "global_vector": [0.1, 0.2],
            }
        )
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

    asyncio.run(
        worker._handle_global_payload(
            {
                "commit": {"accepted_learner_ids": ["learner-0", "learner-1"]},
            }
        )
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

    asyncio.run(
        worker._handle_global_payload(
            {
                "last_commit": {"accepted_learner_ids": ["learner-0", "learner-1"]},
            }
        )
    )

    assert trainer.accepted == 0
    assert worker.in_flight_idempotency_key is None


def test_learner_waits_while_pause_file_exists(tmp_path) -> None:
    worker = LearnerWorker.__new__(LearnerWorker)
    worker.learner_id = "learner-0"
    worker.workdir = tmp_path
    worker.pause_path = tmp_path / "learner-0.pause.json"
    worker.pause_ack_path = tmp_path / "learner-0.paused.json"
    worker.trainer = SimpleNamespace(
        health=lambda: SimpleNamespace(local_step=7, global_version=3),
    )
    worker._write_checkpoint = lambda: None
    events: list[tuple[str, dict]] = []
    worker._log = lambda event_type, payload=None: events.append((event_type, payload or {}))

    async def scenario() -> None:
        worker.pause_path.write_text('{"reason":"restart"}', encoding="utf-8")
        task = asyncio.create_task(worker._wait_while_paused_if_requested())
        for _ in range(20):
            if worker.pause_ack_path.exists():
                break
            await asyncio.sleep(0.01)
        assert worker.pause_ack_path.exists()
        worker.pause_path.unlink()
        await asyncio.wait_for(task, timeout=1.0)

    asyncio.run(scenario())

    assert not worker.pause_ack_path.exists()
    assert events[0][0] == "paused"
    assert events[-1][0] == "resumed"
