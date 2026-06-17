import pytest

from decodilo.errors import InvariantViolation
from decodilo.runtime.learner_checkpoint import (
    load_chunked_learner_checkpoint,
    make_checkpoint,
    write_chunked_learner_checkpoint,
)
from decodilo.runtime.syncer_checkpoint import (
    load_chunked_syncer_checkpoint,
    load_syncer_checkpoint,
    make_syncer_checkpoint,
    write_chunked_syncer_checkpoint,
    write_syncer_checkpoint_atomic,
)
from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.trainer.numpy_convex import NumpyConvexTrainer
from decodilo.trainer.state import TrainerConfig
from decodilo.transport.envelope import MessageType, make_envelope


def test_chunked_learner_checkpoint_roundtrip(tmp_path) -> None:
    checkpoint = make_checkpoint(
        run_id="run",
        learner_id="learner-0",
        local_step=1,
        tokens_processed=10,
        tokens_since_last_sync=10,
        last_global_version_seen=0,
        last_applied_global_version=0,
        throughput_tokens_per_step=10,
        parameter_vector=[1.0, 2.0],
        written_logical_time=1,
    )
    manifest_path = tmp_path / "learner.artifact.json"
    write_chunked_learner_checkpoint(
        manifest_path=manifest_path,
        chunk_store_dir=tmp_path / "store",
        checkpoint=checkpoint,
        chunk_size_bytes=16,
    )

    assert load_chunked_learner_checkpoint(
        manifest_path=manifest_path,
        chunk_store_dir=tmp_path / "store",
    ) == checkpoint


def test_chunked_learner_checkpoint_restores_trainer_state_and_accounting(tmp_path) -> None:
    trainer = NumpyConvexTrainer()
    trainer.initialize(
        run_id="run",
        learner_id="learner-0",
        seed=123,
        initial_state=None,
        config=TrainerConfig(
            vector_dim=4,
            learning_rate=0.05,
            throughput_tokens_per_step=100,
        ),
    )
    trainer.train_local_steps(3)
    before_health = trainer.health()
    state = trainer.get_full_state()
    checkpoint = make_checkpoint(
        run_id="run",
        learner_id="learner-0",
        local_step=state.local_step,
        tokens_processed=state.tokens_processed,
        tokens_since_last_sync=state.tokens_since_last_sync,
        last_global_version_seen=2,
        last_applied_global_version=2,
        throughput_tokens_per_step=100,
        parameter_vector=state.parameters,
        trainer_payload=trainer.checkpoint_payload(),
        written_logical_time=9,
    )
    manifest_path = tmp_path / "learner.artifact.json"
    manifest = write_chunked_learner_checkpoint(
        manifest_path=manifest_path,
        chunk_store_dir=tmp_path / "store",
        checkpoint=checkpoint,
        chunk_size_bytes=64,
    )

    loaded = load_chunked_learner_checkpoint(
        manifest_path=manifest_path,
        chunk_store_dir=tmp_path / "store",
    )
    restored = NumpyConvexTrainer()
    restored.restore_from_checkpoint(loaded.trainer_payload)
    after_health = restored.health()

    assert after_health.state_checksum == before_health.state_checksum
    assert loaded.local_step == state.local_step
    assert loaded.tokens_processed == state.tokens_processed
    assert loaded.last_global_version_seen == 2
    assert loaded.last_applied_global_version == 2

    chunk = manifest.chunk_hashes[0]
    (tmp_path / "store" / "chunks" / chunk[:2] / chunk).write_bytes(b"bad")
    with pytest.raises(InvariantViolation):
        load_chunked_learner_checkpoint(
            manifest_path=manifest_path,
            chunk_store_dir=tmp_path / "store",
        )


def test_missing_chunked_learner_manifest_fails_restore(tmp_path) -> None:
    with pytest.raises(InvariantViolation):
        load_chunked_learner_checkpoint(
            manifest_path=tmp_path / "missing.artifact.json",
            chunk_store_dir=tmp_path / "store",
        )


def test_chunked_syncer_checkpoint_roundtrip_and_corruption_rejected(tmp_path) -> None:
    checkpoint = make_syncer_checkpoint(
        run_id="run",
        global_version=1,
        global_vector=[1.0, 2.0],
        outer_optimizer_state={},
        fragment_store_state={},
        learner_registry_state={},
        idempotency_table={},
        committed_round_state={},
        pending_round_state={},
        metrics_snapshot={},
        event_log_offset=0,
        last_event_id=None,
        written_logical_time=1,
    )
    manifest_path = tmp_path / "syncer.artifact.json"
    manifest = write_chunked_syncer_checkpoint(
        manifest_path=manifest_path,
        chunk_store_dir=tmp_path / "store",
        checkpoint=checkpoint,
        chunk_size_bytes=16,
    )
    assert load_chunked_syncer_checkpoint(
        manifest_path=manifest_path,
        chunk_store_dir=tmp_path / "store",
    ) == checkpoint

    chunk = manifest.chunk_hashes[0]
    chunk_path = (tmp_path / "store" / "chunks" / chunk[:2] / chunk)
    chunk_path.write_bytes(b"bad")
    with pytest.raises(InvariantViolation):
        load_chunked_syncer_checkpoint(
            manifest_path=manifest_path,
            chunk_store_dir=tmp_path / "store",
        )


def test_chunked_syncer_checkpoint_restores_state_and_idempotency(tmp_path) -> None:
    async def scenario() -> None:
        service = SyncerService(
            SyncerServiceConfig(
                run_id="run-syncer-chunked",
                workdir=tmp_path,
                learners=1,
                vector_dim=1,
                min_quorum=1,
            )
        )
        submit = make_envelope(
            run_id="run-syncer-chunked",
            sender_id="learner-0",
            message_type=MessageType.SUBMIT_FRAGMENT,
            idempotency_key="fragment-once",
            payload={
                "vector": [2.0],
                "global_version_seen": 0,
                "tokens": 10,
                "tokens_processed": 10,
            },
        )
        first = await service.handle_envelope(submit)
        service._write_syncer_checkpoint()
        checkpoint = load_syncer_checkpoint(tmp_path / "syncer_checkpoint.json")
        manifest_path = tmp_path / "syncer.artifact.json"
        write_chunked_syncer_checkpoint(
            manifest_path=manifest_path,
            chunk_store_dir=tmp_path / "store",
            checkpoint=checkpoint,
            chunk_size_bytes=64,
        )

        loaded = load_chunked_syncer_checkpoint(
            manifest_path=manifest_path,
            chunk_store_dir=tmp_path / "store",
        )
        (tmp_path / "syncer_checkpoint.json").unlink()
        write_syncer_checkpoint_atomic(tmp_path / "syncer_checkpoint.json", loaded)
        recovered = SyncerService(
            SyncerServiceConfig(
                run_id="run-syncer-chunked",
                workdir=tmp_path,
                learners=1,
                vector_dim=1,
                min_quorum=1,
                recover_from_checkpoint=True,
            )
        )
        duplicate = await recovered.handle_envelope(submit)

        assert first.payload["outcome"] == "committed"
        assert loaded.global_version == 1
        assert loaded.global_vector == [2.0]
        assert "fragment-once" in loaded.idempotency_table
        assert duplicate.payload["duplicate"] is True
        assert recovered.store.global_version == 1
        assert recovered.store.global_vector.tolist() == [2.0]
        assert recovered.store.metrics.useful_tokens == 10

    import asyncio

    asyncio.run(scenario())
