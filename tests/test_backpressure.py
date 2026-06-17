import asyncio
import json
import subprocess
import sys

import numpy as np

from decodilo.runtime.backpressure import BackpressureConfig, BackpressureState
from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.syncer.replay import replay_event_log
from decodilo.transport.envelope import MessageType, make_envelope


def test_pending_fragment_limit_rejects_without_state_corruption() -> None:
    state = BackpressureState(
        BackpressureConfig(
            max_pending_messages_per_learner=10,
            max_pending_fragments_per_learner=1,
            max_inflight_bytes_per_learner=1_000,
            max_total_inflight_bytes=1_000,
        )
    )
    state.begin_fragment("learner-0", message_bytes=100)

    accepted, reason = state.can_accept_fragment("learner-0", message_bytes=100)

    assert not accepted
    assert reason == "max_pending_fragments_per_learner"
    state.reject()
    assert state.metrics.backpressure_rejections == 1


def test_backpressure_rejection_is_idempotent_and_not_useful(tmp_path) -> None:
    async def scenario() -> None:
        service = SyncerService(
            SyncerServiceConfig(
                run_id="run-backpressure",
                workdir=tmp_path,
                learners=1,
                vector_dim=2,
                min_quorum=1,
                max_total_inflight_bytes=1,
            )
        )
        await service.start()
        submit = make_envelope(
            run_id="run-backpressure",
            sender_id="learner-0",
            recipient_id="syncer",
            message_type=MessageType.SUBMIT_FRAGMENT,
            idempotency_key="backpressure-key",
            payload={
                "vector": [2.0, 2.0],
                "global_version_seen": 0,
                "tokens": 10,
                "tokens_processed": 10,
            },
        )

        first = await service.handle_envelope(submit)
        duplicate = await service.handle_envelope(submit)
        await service.handle_envelope(
            make_envelope(
                run_id="run-backpressure",
                sender_id="supervisor",
                message_type=MessageType.SYNCER_SHUTDOWN,
            )
        )
        await service.server.close()

        assert first.message_type == MessageType.BACKPRESSURE_REJECT
        assert duplicate.payload["duplicate"] is True
        assert service.store.metrics.useful_tokens == 0
        np.testing.assert_allclose(service.store.global_vector, np.zeros(2))
        assert service.backpressure.metrics.backpressure_rejections == 1
        replay = replay_event_log(tmp_path / "events.jsonl")
        assert replay.accepted_useful_tokens == 0

    asyncio.run(scenario())


def test_local_report_includes_backpressure_metrics(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--learners",
            "3",
            "--steps",
            "40",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert "backpressure_rejections" in report["metrics"]
    assert "inflight_bytes_peak" in report["metrics"]
    assert report["metrics"]["committed_sync_rounds"] > 0
