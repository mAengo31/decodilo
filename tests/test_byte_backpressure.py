from decodilo.runtime.backpressure import BackpressureConfig, BackpressureState
from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.transport.envelope import MessageType, make_envelope


def test_declared_oversized_payload_rejected_as_byte_pressure() -> None:
    state = BackpressureState(
        BackpressureConfig(
            max_pending_messages_per_learner=10,
            max_pending_fragments_per_learner=10,
            max_inflight_bytes_per_learner=100,
            max_total_inflight_bytes=100,
        )
    )

    accepted, reason = state.can_accept_fragment("learner-0", message_bytes=101)
    assert accepted is False
    state.reject(reason)
    assert state.metrics.byte_pressure == 1


def test_byte_pressure_is_per_learner_until_global_budget_exhausted() -> None:
    state = BackpressureState(
        BackpressureConfig(
            max_pending_messages_per_learner=10,
            max_pending_fragments_per_learner=10,
            max_inflight_bytes_per_learner=100,
            max_total_inflight_bytes=150,
        )
    )

    assert state.can_accept_fragment("learner-0", message_bytes=90)[0] is True
    state.begin_fragment("learner-0", message_bytes=90)
    assert state.can_accept_fragment("learner-1", message_bytes=50)[0] is True
    assert state.can_accept_fragment("learner-1", message_bytes=70)[0] is False


def test_syncer_rejects_declared_oversized_payload_and_logs_reason(tmp_path) -> None:
    import asyncio

    async def scenario() -> None:
        service = SyncerService(
            SyncerServiceConfig(
                run_id="run-backpressure",
                workdir=tmp_path,
                learners=1,
                vector_dim=1,
                min_quorum=1,
                max_inflight_bytes_per_learner=128,
                max_total_inflight_bytes=128,
            )
        )
        envelope = make_envelope(
            run_id="run-backpressure",
            sender_id="learner-0",
            message_type=MessageType.SUBMIT_FRAGMENT,
            idempotency_key="too-large",
            payload={
                "vector": [1.0],
                "global_version_seen": 0,
                "tokens": 10,
                "tokens_processed": 10,
                "payload_bytes": 10_000,
            },
        )

        response = await service.handle_envelope(envelope)

        assert response.message_type == MessageType.BACKPRESSURE_REJECT
        assert response.payload["reason"] == "max_inflight_bytes_per_learner"
        assert service.backpressure.metrics.byte_pressure == 1
        assert service.store.metrics.useful_tokens == 0
        event_text = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
        assert "backpressure_rejected" in event_text
        assert "max_inflight_bytes_per_learner" in event_text

    asyncio.run(scenario())


def test_under_declared_payload_and_duplicate_cannot_bypass_limits(tmp_path) -> None:
    import asyncio

    async def scenario() -> None:
        service = SyncerService(
            SyncerServiceConfig(
                run_id="run-underdeclared",
                workdir=tmp_path,
                learners=1,
                vector_dim=1,
                min_quorum=1,
            )
        )
        envelope = make_envelope(
            run_id="run-underdeclared",
            sender_id="learner-0",
            message_type=MessageType.SUBMIT_FRAGMENT,
            idempotency_key="same-underdeclared",
            payload={
                "vector": [1.0],
                "global_version_seen": 0,
                "tokens": 10,
                "tokens_processed": 10,
                "payload_bytes": 1,
                "padding": "x" * 5000,
            },
        )

        first = await service.handle_envelope(envelope)
        second = await service.handle_envelope(envelope)

        assert first.message_type == MessageType.BACKPRESSURE_REJECT
        assert first.payload["reason"] == "size_mismatch"
        assert second.payload["duplicate"] is True
        assert service.backpressure.metrics.byte_pressure == 1
        assert service.store.metrics.useful_tokens == 0

    asyncio.run(scenario())
