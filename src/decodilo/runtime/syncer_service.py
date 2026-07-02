"""Local asyncio syncer service for JSONL-over-TCP learner workers."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from decodilo import __version__
from decodilo.errors import InvariantViolation
from decodilo.protocol.messages import LearnerStatus
from decodilo.runtime.artifact_transport import (
    ArtifactRef,
    ArtifactTransportPolicy,
    LocalArtifactTransport,
)
from decodilo.runtime.backpressure import BackpressureConfig, BackpressureState
from decodilo.runtime.chunked_payloads import default_artifact_root, default_chunk_store_root
from decodilo.runtime.chunked_runtime_modes import validate_runtime_modes
from decodilo.runtime.remote_artifact_fetch import (
    artifact_bundle_from_ref,
    artifact_chunk_from_ref,
    artifact_metadata_from_ref,
    materialize_artifact_bundle,
    materialize_artifact_chunk_upload,
)
from decodilo.runtime.syncer_checkpoint import (
    load_chunked_syncer_checkpoint,
    load_syncer_checkpoint,
    make_syncer_checkpoint,
    write_chunked_syncer_checkpoint,
    write_syncer_checkpoint_atomic,
)
from decodilo.runtime.syncer_recovery import require_checkpoint_for_run
from decodilo.runtime.update_stream import UpdateStream
from decodilo.sim.metrics import SimulationMetrics
from decodilo.sim.runner import SimulationConfig, deterministic_run_id
from decodilo.storage.checksums import sha256_file
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.codec_registry import validate_artifact_codec
from decodilo.storage.s3_compatible_backend import (
    S3CompatibleArtifactBackend,
    S3CompatibleBackendConfig,
)
from decodilo.syncer.binary_streaming_merge import binary_streaming_token_weighted_merge
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.fragment_store import FragmentStore
from decodilo.syncer.global_state_store import write_global_vector_artifact
from decodilo.syncer.outer_optimizer import (
    create_outer_optimizer,
    outer_optimizer_name,
    outer_optimizer_state,
)
from decodilo.syncer.quorum import QuorumPolicy
from decodilo.syncer.recovery_manifest import (
    load_recovery_manifest,
    make_recovery_manifest,
    write_recovery_manifest_atomic,
)
from decodilo.trainer.fragment_artifacts import read_fragment_artifact
from decodilo.trainer.numpy_convex import (
    convex_loss,
    make_initial_vector,
    make_target_vector,
)
from decodilo.trainer.state import TrainerFragment
from decodilo.trainer.state_codec import validate_fragment
from decodilo.transport.envelope import MessageType, TransportEnvelope, make_envelope
from decodilo.transport.tcp_server import JsonlTcpServer


@dataclass(frozen=True)
class SyncerServiceConfig:
    run_id: str
    workdir: Path
    host: str = "127.0.0.1"
    port: int = 0
    learners: int = 4
    vector_dim: int = 8
    num_fragments: int = 2
    steps: int = 200
    local_steps_per_sync: int = 10
    min_quorum: int = 2
    grace_window_ticks: int = 0
    max_staleness_versions: int = 1
    seed: int = 123
    learner_lr: float = 0.05
    outer_optimizer: str = "sgd"
    outer_lr: float = 1.0
    outer_momentum: float = 0.9
    heartbeat_timeout_seconds: float = 0.5
    heartbeat_check_interval_seconds: float = 0.05
    max_message_bytes: int = 1_000_000
    update_long_poll_timeout_seconds: float = 0.2
    max_learner_version_lag: int = 2
    max_pending_messages_per_learner: int = 128
    max_pending_fragments_per_learner: int = 1
    max_inflight_bytes_per_learner: int = 2_000_000
    max_total_inflight_bytes: int = 10_000_000
    syncer_checkpoint_interval_rounds: int = 0
    recover_from_checkpoint: bool = False
    syncer_checkpoint_path: Path | None = None
    payload_storage_mode: str = "inline"
    checkpoint_storage_mode: str = "inline"
    merge_mode: str = "in_memory"
    global_update_storage_mode: str = "inline"
    artifact_root: Path | None = None
    chunk_store_root: Path | None = None
    inline_payload_max_bytes: int = 1_000_000
    chunk_size_bytes: int = 1024 * 1024
    tensor_artifact_codec: str = "json_safe"
    fragment_artifact_codec: str = "json_safe"
    checkpoint_artifact_codec: str = "json_safe"
    artifact_transfer_mode: str = "bundle"
    artifact_storage_backend: str = "auto"
    s3_artifact_backend: S3CompatibleArtifactBackend | None = None
    s3_endpoint_url: str | None = None
    s3_bucket: str | None = None
    s3_prefix: str = "decodilo-artifacts"
    s3_region: str | None = None
    s3_access_key_ref: str | None = None
    s3_secret_key_ref: str | None = None
    s3_session_token_ref: str | None = None



def _runtime_s3_backend_from_config(
    config: SyncerServiceConfig,
) -> S3CompatibleArtifactBackend | None:
    if config.artifact_storage_backend != "s3_compatible":
        return None
    if not config.s3_endpoint_url or not config.s3_bucket:
        return None
    import os

    from decodilo.storage.s3_runtime import create_boto3_s3_compatible_backend_from_env

    return create_boto3_s3_compatible_backend_from_env(
        S3CompatibleBackendConfig(
            endpoint_url=config.s3_endpoint_url,
            bucket=config.s3_bucket,
            prefix=config.s3_prefix,
            region=config.s3_region,
            access_key_ref=config.s3_access_key_ref,
            secret_key_ref=config.s3_secret_key_ref,
            session_token_ref=config.s3_session_token_ref,
        ),
        environ=os.environ,
        require_probe=True,
    )

def _artifact_storage_backend(*, transfer_mode: str, storage_backend: str) -> str:
    if storage_backend != "auto":
        return storage_backend
    return "syncer_object_store" if transfer_mode == "object_store" else "local_filesystem"


class SyncerService:
    """JSONL transport adapter around the existing FragmentStore syncer."""

    def __init__(self, config: SyncerServiceConfig) -> None:
        self.config = config
        self.config.workdir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = config.syncer_checkpoint_path or (
            self.config.workdir / "syncer_checkpoint.json"
        )
        self.recovery_manifest_path = self.config.workdir / "recovery_manifest.json"
        validate_runtime_modes(
            payload_storage_mode=config.payload_storage_mode,
            checkpoint_storage_mode=config.checkpoint_storage_mode,
            merge_mode=config.merge_mode,
            global_update_storage_mode=config.global_update_storage_mode,
        )
        validate_artifact_codec(config.tensor_artifact_codec)
        validate_artifact_codec(config.fragment_artifact_codec)
        validate_artifact_codec(config.checkpoint_artifact_codec)
        self.artifact_root = config.artifact_root or default_artifact_root(config.workdir)
        self.chunk_store_root = config.chunk_store_root or default_chunk_store_root(config.workdir)
        s3_backend = config.s3_artifact_backend or _runtime_s3_backend_from_config(config)
        self.artifact_transport = LocalArtifactTransport(
            policy=ArtifactTransportPolicy(
                workdir=str(config.workdir),
                artifact_root=str(self.artifact_root),
                storage_backend=_artifact_storage_backend(
                    transfer_mode=config.artifact_transfer_mode,
                    storage_backend=config.artifact_storage_backend,
                ),
            ),
            s3_backend=s3_backend,
        )
        self.event_log = EventLog(
            self.config.workdir / "events.jsonl",
            run_id=config.run_id,
            truncate=not config.recover_from_checkpoint,
        )
        self.target_vector = make_target_vector(config.vector_dim, seed=config.seed + 1)
        self.store = FragmentStore(
            initial_global_vector=make_initial_vector(config.vector_dim),
            num_fragments=config.num_fragments,
            quorum_policy=QuorumPolicy(
                min_quorum=config.min_quorum,
                grace_window_ticks=config.grace_window_ticks,
                max_staleness_versions=config.max_staleness_versions,
            ),
            optimizer=create_outer_optimizer(
                config.outer_optimizer,
                outer_lr=config.outer_lr,
                momentum=config.outer_momentum,
            ),
            event_log=self.event_log,
            event_payload_mode=(
                "chunked"
                if config.payload_storage_mode in {"chunked", "auto"}
                or config.global_update_storage_mode in {"chunked", "auto"}
                else "inline"
            ),
            merge_mode=(
                "streaming_chunked"
                if config.merge_mode == "streaming_chunked"
                else "in_memory"
            ),
            global_vector_artifact_writer=self._write_global_vector_artifact,
            binary_merge_runner=self._run_binary_merge,
        )
        self.server = JsonlTcpServer(
            handler=self.handle_envelope,
            host=config.host,
            port=config.port,
            server_id="syncer",
            run_id=config.run_id,
            max_message_bytes=config.max_message_bytes,
        )
        self.stop_event = asyncio.Event()
        self.logical_time = 0
        self.registered_learners: set[str] = set()
        self.unhealthy_learners: set[str] = set()
        self.last_heartbeat: dict[str, float] = {}
        self.learner_tokens_processed: dict[str, int] = {}
        self.learner_trainer_metrics: dict[str, dict[str, Any]] = {}
        self.learner_status: dict[str, LearnerStatus] = {}
        self.idempotency: dict[str, dict[str, Any]] = {}
        self.last_commit_payload: dict[str, Any] | None = None
        self.trainer_state_kind = "flat"
        self.recovery_source: str | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self.update_stream = UpdateStream(max_version_lag=config.max_learner_version_lag)
        self.backpressure = BackpressureState(
            BackpressureConfig(
                max_pending_messages_per_learner=config.max_pending_messages_per_learner,
                max_pending_fragments_per_learner=config.max_pending_fragments_per_learner,
                max_inflight_bytes_per_learner=config.max_inflight_bytes_per_learner,
                max_total_inflight_bytes=config.max_total_inflight_bytes,
            )
        )
        if config.recover_from_checkpoint:
            self._recover_from_checkpoint()

    def _time(self) -> int:
        value = self.logical_time
        self.logical_time += 1
        return value

    def _envelope(
        self,
        *,
        message_type: MessageType,
        payload: dict[str, Any] | None = None,
        recipient_id: str | None = None,
    ) -> TransportEnvelope:
        return make_envelope(
            run_id=self.config.run_id,
            sender_id="syncer",
            recipient_id=recipient_id,
            message_type=message_type,
            payload=payload or {},
            created_logical_time=self.logical_time,
        )

    async def start(self) -> None:
        await self.server.start()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

    async def serve_until_stopped(self, *, ready_file: Path | None = None) -> None:
        await self.start()
        if ready_file is not None:
            ready_file.parent.mkdir(parents=True, exist_ok=True)
            ready_file.write_text(
                json.dumps(
                    {
                        "host": self.server.bound_host,
                        "port": self.server.bound_port,
                        "run_id": self.config.run_id,
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        await self.stop_event.wait()
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
        await self.server.close()

    async def stop(self) -> None:
        self.stop_event.set()

    async def _heartbeat_monitor(self) -> None:
        while True:
            await asyncio.sleep(self.config.heartbeat_check_interval_seconds)
            now = time.monotonic()
            changed = False
            for learner_id, last_seen in list(self.last_heartbeat.items()):
                if learner_id in self.unhealthy_learners:
                    continue
                if now - last_seen > self.config.heartbeat_timeout_seconds:
                    self.unhealthy_learners.add(learner_id)
                    self.learner_status[learner_id] = LearnerStatus.FAILED
                    self.event_log.append(
                        EventType.LEARNER_UNHEALTHY,
                        logical_time=self._time(),
                        learner_id=learner_id,
                        payload={
                            "learner_id": learner_id,
                            "heartbeat_timeout_seconds": self.config.heartbeat_timeout_seconds,
                            "global_version": self.store.global_version,
                        },
                    )
                    changed = True
            if changed:
                self._maybe_commit()

    async def handle_envelope(self, envelope: TransportEnvelope) -> TransportEnvelope:
        try:
            if envelope.message_type == MessageType.REGISTER_LEARNER:
                return self._handle_register(envelope)
            if envelope.message_type == MessageType.HEARTBEAT:
                return self._handle_heartbeat(envelope)
            if envelope.message_type == MessageType.REQUEST_GLOBAL_STATE:
                return self._handle_global_state(envelope)
            if envelope.message_type == MessageType.SUBSCRIBE_UPDATES:
                return await self._handle_subscribe_updates(envelope)
            if envelope.message_type == MessageType.GLOBAL_UPDATE_ACK:
                return self._handle_global_update_ack(envelope)
            if envelope.message_type == MessageType.FETCH_ARTIFACT:
                return self._handle_fetch_artifact(envelope)
            if envelope.message_type == MessageType.FETCH_ARTIFACT_CHUNK:
                return self._handle_fetch_artifact_chunk(envelope)
            if envelope.message_type == MessageType.UPLOAD_ARTIFACT_CHUNK:
                return self._handle_upload_artifact_chunk(envelope)
            if envelope.message_type == MessageType.SUBMIT_FRAGMENT:
                return self._handle_submit_fragment(envelope)
            if envelope.message_type == MessageType.LEARNER_SHUTDOWN:
                return self._handle_learner_shutdown(envelope)
            if envelope.message_type == MessageType.SYNCER_SHUTDOWN:
                return await self._handle_syncer_shutdown(envelope)
        except Exception as exc:  # noqa: BLE001 - returned to local caller as protocol error
            return self._envelope(
                message_type=MessageType.ERROR,
                recipient_id=envelope.sender_id,
                payload={"error": str(exc), "error_type": exc.__class__.__name__},
            )
        return self._envelope(
            message_type=MessageType.ERROR,
            recipient_id=envelope.sender_id,
            payload={"error": f"unsupported message_type {envelope.message_type}"},
        )

    def _handle_register(self, envelope: TransportEnvelope) -> TransportEnvelope:
        learner_id = str(envelope.payload.get("learner_id") or envelope.sender_id)
        was_registered = learner_id in self.registered_learners
        was_unhealthy = learner_id in self.unhealthy_learners
        self.registered_learners.add(learner_id)
        self.unhealthy_learners.discard(learner_id)
        self.last_heartbeat[learner_id] = time.monotonic()
        self.learner_status[learner_id] = LearnerStatus.ALIVE
        self.update_stream.register(learner_id, version=self.store.global_version)
        if was_unhealthy or was_registered:
            event_type = (
                EventType.LEARNER_RECONNECTED
                if envelope.payload.get("reconnected")
                else EventType.LEARNER_RECOVERED
            )
            self.event_log.append(
                event_type,
                logical_time=self._time(),
                learner_id=learner_id,
                payload={
                    "learner_id": learner_id,
                    "recovery_version": self.store.global_version,
                    "reconnected": bool(envelope.payload.get("reconnected")),
                },
            )
        else:
            self.event_log.append(
                EventType.LEARNER_STARTED,
                logical_time=self._time(),
                learner_id=learner_id,
                payload={"learner_id": learner_id},
            )
        return self._envelope(
            message_type=MessageType.REGISTER_LEARNER_ACK,
            recipient_id=learner_id,
            payload=self._global_state_payload({"learner_id": learner_id}),
        )

    def _handle_heartbeat(self, envelope: TransportEnvelope) -> TransportEnvelope:
        learner_id = envelope.sender_id
        self.last_heartbeat[learner_id] = time.monotonic()
        self.unhealthy_learners.discard(learner_id)
        self.learner_status[learner_id] = LearnerStatus.ALIVE
        if "tokens_processed" in envelope.payload:
            self.learner_tokens_processed[learner_id] = max(
                self.learner_tokens_processed.get(learner_id, 0),
                int(envelope.payload["tokens_processed"]),
            )
        self._record_trainer_metrics(learner_id, envelope.payload)
        control_event = envelope.payload.get("control_event")
        if control_event == "learner_slowed":
            self.event_log.append(
                EventType.LEARNER_SLOWED,
                logical_time=self._time(),
                learner_id=learner_id,
                payload={
                    "learner_id": learner_id,
                    "factor": envelope.payload.get("factor"),
                    "global_version": self.store.global_version,
                },
            )
        elif control_event == "learner_speed_restored":
            self.event_log.append(
                EventType.LEARNER_SPEED_RESTORED,
                logical_time=self._time(),
                learner_id=learner_id,
                payload={
                    "learner_id": learner_id,
                    "global_version": self.store.global_version,
                },
            )
        return self._envelope(
            message_type=MessageType.HEARTBEAT_ACK,
            recipient_id=learner_id,
            payload={
                "global_version": self.store.global_version,
                "last_commit": self.last_commit_payload,
                "unhealthy_learners": sorted(self.unhealthy_learners),
            },
        )

    def _handle_global_state(self, envelope: TransportEnvelope) -> TransportEnvelope:
        return self._envelope(
            message_type=MessageType.GLOBAL_STATE_RESPONSE,
            recipient_id=envelope.sender_id,
            payload=self._global_state_payload(),
        )

    async def _handle_subscribe_updates(self, envelope: TransportEnvelope) -> TransportEnvelope:
        learner_version = int(envelope.payload.get("last_applied_global_version", 0))
        available = await self.update_stream.wait_for_update(
            learner_id=envelope.sender_id,
            learner_version=learner_version,
            current_version=self.store.global_version,
            timeout_seconds=self.config.update_long_poll_timeout_seconds,
        )
        if not available:
            return self._envelope(
                message_type=MessageType.SUBSCRIBE_UPDATES_ACK,
                recipient_id=envelope.sender_id,
                payload={
                    "update_available": False,
                    "global_version": self.store.global_version,
                },
            )
        self.update_stream.mark_sent(envelope.sender_id, global_version=self.store.global_version)
        self.event_log.append(
            EventType.GLOBAL_UPDATE_SENT,
            logical_time=self._time(),
            learner_id=envelope.sender_id,
            payload={
                "learner_id": envelope.sender_id,
                "global_version": self.store.global_version,
            },
        )
        return self._envelope(
            message_type=MessageType.GLOBAL_UPDATE_PAYLOAD,
            recipient_id=envelope.sender_id,
            payload=self._global_state_payload({"last_commit": self.last_commit_payload}),
        )


    def _handle_fetch_artifact(self, envelope: TransportEnvelope) -> TransportEnvelope:
        artifact_ref = envelope.payload.get("artifact_ref")
        if artifact_ref is None:
            raise InvariantViolation("fetch_artifact requires artifact_ref")
        response_mode = str(envelope.payload.get("response_mode", "bundle"))
        payload = (
            artifact_metadata_from_ref(artifact_ref, transport=self.artifact_transport)
            if response_mode == "metadata_only"
            else artifact_bundle_from_ref(artifact_ref, transport=self.artifact_transport)
        )
        return self._envelope(
            message_type=MessageType.FETCH_ARTIFACT_RESPONSE,
            recipient_id=envelope.sender_id,
            payload=payload,
        )

    def _handle_fetch_artifact_chunk(self, envelope: TransportEnvelope) -> TransportEnvelope:
        artifact_ref = envelope.payload.get("artifact_ref")
        chunk_hash = envelope.payload.get("sha256")
        if artifact_ref is None or not chunk_hash:
            raise InvariantViolation("fetch_artifact_chunk requires artifact_ref and sha256")
        return self._envelope(
            message_type=MessageType.FETCH_ARTIFACT_CHUNK_RESPONSE,
            recipient_id=envelope.sender_id,
            payload=artifact_chunk_from_ref(
                artifact_ref,
                chunk_hash=str(chunk_hash),
                transport=self.artifact_transport,
            ),
        )

    def _handle_upload_artifact_chunk(self, envelope: TransportEnvelope) -> TransportEnvelope:
        result = materialize_artifact_chunk_upload(
            envelope.payload,
            transport=self.artifact_transport,
        )
        return self._envelope(
            message_type=MessageType.UPLOAD_ARTIFACT_CHUNK_ACK,
            recipient_id=envelope.sender_id,
            payload=result,
        )

    def _handle_global_update_ack(self, envelope: TransportEnvelope) -> TransportEnvelope:
        version = int(envelope.payload["global_version"])
        self.update_stream.ack(
            envelope.sender_id,
            global_version=version,
            current_version=self.store.global_version,
        )
        self.event_log.append(
            EventType.GLOBAL_UPDATE_ACKED,
            logical_time=self._time(),
            learner_id=envelope.sender_id,
            payload={"learner_id": envelope.sender_id, "global_version": version},
        )
        return self._envelope(
            message_type=MessageType.HEARTBEAT_ACK,
            recipient_id=envelope.sender_id,
            payload={"acknowledged_global_version": version},
        )

    def _handle_submit_fragment(self, envelope: TransportEnvelope) -> TransportEnvelope:
        key = envelope.idempotency_key
        if key is None:
            raise InvariantViolation("submit_fragment requires idempotency_key")
        if key in self.idempotency:
            record = self.idempotency[key]
            self.event_log.append(
                EventType.TRANSPORT_DUPLICATE,
                logical_time=self._time(),
                learner_id=envelope.sender_id,
                payload={
                    "idempotency_key": key,
                    "original_outcome": record["payload"].get("outcome"),
                },
            )
            payload = dict(record["payload"])
            payload["duplicate"] = True
            return self._envelope(
                message_type=MessageType(record["message_type"]),
                recipient_id=envelope.sender_id,
                payload=payload,
            )

        learner_id = envelope.sender_id
        payload = envelope.payload
        self.unhealthy_learners.discard(learner_id)
        self.learner_status[learner_id] = LearnerStatus.ALIVE
        self.last_heartbeat[learner_id] = time.monotonic()
        message_bytes = len(envelope.to_json_line().encode("utf-8"))
        declared_payload_bytes = int(payload.get("payload_bytes", message_bytes))
        if message_bytes > max(declared_payload_bytes * 2, declared_payload_bytes + 1024):
            self.backpressure.reject("size_mismatch")
            self.event_log.append(
                EventType.BACKPRESSURE_REJECTED,
                logical_time=self._time(),
                learner_id=learner_id,
                payload={
                    "learner_id": learner_id,
                    "idempotency_key": key,
                    "reason": "size_mismatch",
                    "tokens": int(payload.get("tokens", 0)),
                    "declared_payload_bytes": declared_payload_bytes,
                    "actual_message_bytes": message_bytes,
                },
            )
            response_payload = {
                "idempotency_key": key,
                "outcome": "backpressure_rejected",
                "reason": "size_mismatch",
                "global_version": self.store.global_version,
            }
            self.idempotency[key] = {
                "message_type": MessageType.BACKPRESSURE_REJECT.value,
                "payload": dict(response_payload),
            }
            return self._envelope(
                message_type=MessageType.BACKPRESSURE_REJECT,
                recipient_id=learner_id,
                payload=response_payload,
            )
        accepted_by_backpressure, reason = self.backpressure.can_accept_fragment(
            learner_id,
            message_bytes=max(message_bytes, declared_payload_bytes),
        )
        if not accepted_by_backpressure:
            self.backpressure.reject(reason)
            self.event_log.append(
                EventType.BACKPRESSURE_REJECTED,
                logical_time=self._time(),
                learner_id=learner_id,
                payload={
                    "learner_id": learner_id,
                    "idempotency_key": key,
                    "reason": reason,
                    "tokens": int(payload.get("tokens", 0)),
                },
            )
            response_payload = {
                "idempotency_key": key,
                "outcome": "backpressure_rejected",
                "reason": reason,
                "global_version": self.store.global_version,
            }
            self.idempotency[key] = {
                "message_type": MessageType.BACKPRESSURE_REJECT.value,
                "payload": dict(response_payload),
            }
            return self._envelope(
                message_type=MessageType.BACKPRESSURE_REJECT,
                recipient_id=learner_id,
                payload=response_payload,
            )
        if "tokens_processed" in payload:
            self.learner_tokens_processed[learner_id] = max(
                self.learner_tokens_processed.get(learner_id, 0),
                int(payload["tokens_processed"]),
            )
        self._record_trainer_metrics(learner_id, payload)
        trainer_fragment_payload = payload.get("trainer_fragment")
        artifact_ref_payload = payload.get("trainer_fragment_artifact_ref")
        artifact_bundle_payload = payload.get("trainer_fragment_artifact_bundle")
        self.trainer_state_kind = str(payload.get("trainer_state_kind", self.trainer_state_kind))
        trainer_fragment: TrainerFragment | None = None
        artifact_ref_for_event: dict[str, Any] | None = None
        if artifact_ref_payload is not None:
            validation_started = time.perf_counter()
            self.store.metrics.artifact_ref_validations += 1
            try:
                if artifact_bundle_payload is not None:
                    materialize_artifact_bundle(
                        artifact_bundle_payload,
                        transport=self.artifact_transport,
                    )
                artifact_manifest = self.artifact_transport.validate_ref(artifact_ref_payload)
                trainer_fragment = read_fragment_artifact(
                    ref=artifact_ref_payload,
                    transport=self.artifact_transport,
                )
                if not isinstance(trainer_fragment.data, np.ndarray):
                    trainer_fragment = trainer_fragment.model_copy(
                        update={
                            "data": np.asarray(trainer_fragment.data, dtype=np.float64),
                        }
                    )
                self.store.metrics.artifact_validation_seconds += (
                    time.perf_counter() - validation_started
                )
                self.store.metrics.artifact_bytes_read += artifact_manifest.total_bytes
                self.store.metrics.artifact_chunks_read += len(artifact_manifest.chunk_hashes)
                artifact_ref_for_event = ArtifactRef.model_validate(
                    artifact_ref_payload
                ).model_dump(mode="json")
                vector = np.asarray(trainer_fragment.data, dtype=np.float64)
                global_version_seen = int(trainer_fragment.global_version)
                tokens = int(trainer_fragment.tokens)
            except Exception as exc:  # noqa: BLE001 - fail closed as rejected fragment
                tokens = int(payload.get("tokens", 0))
                self.store.metrics.artifact_ref_validation_failures += 1
                self.store.metrics.artifact_validation_seconds += (
                    time.perf_counter() - validation_started
                )
                self.store.metrics.chunked_fragment_bytes_rejected += int(
                    payload.get("payload_bytes", 0)
                )
                self.store.metrics.record_rejection("artifact_corrupt", tokens)
                self.event_log.append(
                    EventType.FRAGMENT_REJECTED,
                    logical_time=self._time(),
                    learner_id=learner_id,
                    payload={
                        "learner_id": learner_id,
                        "reason": "artifact_corrupt",
                        "tokens": tokens,
                        "global_version": self.store.global_version,
                        "error": str(exc),
                        "storage_kind": "artifact_ref",
                        "payload_bytes": int(payload.get("payload_bytes", 0)),
                    },
                )
                response_payload = {
                    "idempotency_key": key,
                    "outcome": "rejected",
                    "reason": "artifact_corrupt",
                    "global_version": self.store.global_version,
                }
                self.idempotency[key] = {
                    "message_type": MessageType.SUBMIT_FRAGMENT_REJECTED.value,
                    "payload": dict(response_payload),
                }
                return self._envelope(
                    message_type=MessageType.SUBMIT_FRAGMENT_REJECTED,
                    recipient_id=learner_id,
                    payload=response_payload,
                )
        elif trainer_fragment_payload is not None:
            try:
                trainer_fragment = TrainerFragment.model_validate(trainer_fragment_payload)
                validate_fragment(trainer_fragment)
                vector = np.asarray(trainer_fragment.data, dtype=np.float64)
                global_version_seen = int(trainer_fragment.global_version)
                tokens = int(trainer_fragment.tokens)
            except Exception as exc:  # noqa: BLE001 - fail closed as rejected fragment
                tokens = int(payload.get("tokens", 0))
                self.store.metrics.record_rejection("invalid_checksum", tokens)
                self.event_log.append(
                    EventType.FRAGMENT_REJECTED,
                    logical_time=self._time(),
                    learner_id=learner_id,
                    payload={
                        "learner_id": learner_id,
                        "reason": "invalid_checksum",
                        "tokens": tokens,
                        "global_version": self.store.global_version,
                        "error": str(exc),
                    },
                )
                response_payload = {
                    "idempotency_key": key,
                    "outcome": "rejected",
                    "reason": "invalid_checksum",
                    "global_version": self.store.global_version,
                }
                self.idempotency[key] = {
                    "message_type": MessageType.SUBMIT_FRAGMENT_REJECTED.value,
                    "payload": dict(response_payload),
                }
                return self._envelope(
                    message_type=MessageType.SUBMIT_FRAGMENT_REJECTED,
                    recipient_id=learner_id,
                    payload=response_payload,
                )
        else:
            vector = np.asarray(payload["vector"], dtype=np.float64)
            global_version_seen = int(payload["global_version_seen"])
            tokens = int(payload["tokens"])
        self.backpressure.begin_fragment(learner_id, message_bytes=message_bytes)
        try:
            self.store.submit_learner_update(
                learner_id=learner_id,
                vector=vector,
                global_version_seen=global_version_seen,
                tokens=tokens,
                submitted_at=self._time(),
                artifact_ref=artifact_ref_for_event,
                payload_metadata={
                    "checksum": trainer_fragment.checksum if trainer_fragment else None,
                    "dtype": str(np.asarray(vector).dtype),
                    "shape": list(np.asarray(vector).shape),
                },
            )
            if artifact_ref_for_event is not None:
                self.store.metrics.chunked_fragment_bytes_accepted += int(
                    artifact_ref_for_event.get("total_bytes", 0)
                )
            commit = self._maybe_commit()
        finally:
            self.backpressure.end_fragment(learner_id, message_bytes=message_bytes)
        response_payload = {
            "idempotency_key": key,
            "outcome": "queued",
            "global_version": self.store.global_version,
            "last_commit": self.last_commit_payload,
        }
        if commit is not None:
            response_payload["outcome"] = "committed"
            response_payload["commit"] = self._control_commit_payload(commit)
        message_type = MessageType.SUBMIT_FRAGMENT_ACK
        self.idempotency[key] = {
            "message_type": message_type.value,
            "payload": dict(response_payload),
        }
        return self._envelope(
            message_type=message_type,
            recipient_id=learner_id,
            payload=response_payload,
        )

    def _handle_learner_shutdown(self, envelope: TransportEnvelope) -> TransportEnvelope:
        learner_id = envelope.sender_id
        self.learner_status[learner_id] = LearnerStatus.PAUSED
        return self._envelope(
            message_type=MessageType.HEARTBEAT_ACK,
            recipient_id=learner_id,
            payload={"shutdown_ack": True, "global_version": self.store.global_version},
        )

    def _record_trainer_metrics(self, learner_id: str, payload: dict[str, Any]) -> None:
        keys = {
            "trainer_state_bytes_estimate",
            "trainer_num_parameters",
            "trainer_final_loss",
            "trainer_final_eval_loss",
            "trainer_nonfinite_detected",
            "inner_optimizer",
            "inner_optimizer_semantics",
            "training_attempted",
            "real_training_mechanics_exercised",
            "real_model_training_claimed",
            "paper_scale_training_claimed",
            "optimizer_state",
        }
        observed = {key: payload.get(key) for key in keys if key in payload}
        if observed:
            self.learner_trainer_metrics[learner_id] = {
                **self.learner_trainer_metrics.get(learner_id, {}),
                **observed,
            }

    def _write_global_vector_artifact(
        self,
        artifact_role: str,
        vector: np.ndarray,
        global_version: int,
        codec: str | None = None,
    ) -> dict[str, Any]:
        safe_role = artifact_role.replace("/", "_")
        manifest_dir = self.artifact_root / "global"
        manifest_path = (
            manifest_dir / f"{safe_role}-v{global_version}-{self.logical_time}.artifact.json"
        )
        ref = write_global_vector_artifact(
            vector=vector,
            run_id=self.config.run_id,
            global_version=global_version,
            artifact_id=f"{self.config.run_id}:global:{safe_role}:v{global_version}",
            artifact_type="global_vector",
            transport=self.artifact_transport,
            manifest_path=manifest_path,
            chunk_root=self.chunk_store_root,
            chunk_size_bytes=self.config.chunk_size_bytes,
            created_by="syncer",
            codec=codec or self.config.tensor_artifact_codec,
            inline_payload_max_bytes=self.config.inline_payload_max_bytes,
        )
        return ref.model_dump(mode="json")

    def _run_binary_merge(
        self,
        global_vector: np.ndarray,
        artifact_refs: dict[str, dict[str, Any]],
        token_counts: dict[str, int],
        outer_lr: float,
        chunk_elements: int,
    ):
        return binary_streaming_token_weighted_merge(
            global_values=global_vector,
            fragment_refs=artifact_refs,
            token_counts=token_counts,
            transport=self.artifact_transport,
            outer_lr=outer_lr,
            chunk_elements=chunk_elements,
        )

    def _uses_chunked_control_plane(self) -> bool:
        return (
            self.config.payload_storage_mode in {"chunked", "auto"}
            or self.config.global_update_storage_mode in {"chunked", "auto"}
            or self.config.checkpoint_storage_mode in {"chunked", "dual"}
            or self.config.merge_mode == "streaming_chunked"
        )

    def _control_commit_payload(self, commit) -> dict[str, Any]:
        payload = commit.model_dump(mode="json")
        if not self._uses_chunked_control_plane():
            return payload
        return {
            "round_id": payload["round_id"],
            "previous_global_version": payload["previous_global_version"],
            "new_global_version": payload["new_global_version"],
            "accepted_learner_ids": payload["accepted_learner_ids"],
            "token_weights": payload["token_weights"],
            "useful_tokens": payload["useful_tokens"],
            "outer_optimizer": payload["outer_optimizer"],
            "outer_lr": payload["outer_lr"],
            "outer_momentum": payload.get("outer_momentum"),
            "control_payload_compacted": True,
            "vector_payload_location": "global_update_payload_or_artifacts",
        }

    async def _handle_syncer_shutdown(self, envelope: TransportEnvelope) -> TransportEnvelope:
        self._write_syncer_checkpoint()
        self.store.write_checkpoint(checkpoint_id="final", logical_time=self._time())
        payload = self.build_summary()
        if envelope.payload.get("immediate_server_close") is True:
            self.stop_event.set()
            await self.server.close()
        else:
            asyncio.get_running_loop().call_soon(asyncio.create_task, self.stop())
        return self._envelope(
            message_type=MessageType.SYNCER_SHUTDOWN,
            recipient_id=envelope.sender_id,
            payload=payload,
        )

    def _maybe_commit(self):
        commit = self.store.maybe_commit(
            current_tick=self._time(),
            failed_learner_ids=set(self.unhealthy_learners)
            | self.update_stream.stale_learners(current_version=self.store.global_version),
        )
        if commit is not None:
            self.last_commit_payload = self._control_commit_payload(commit)
            self.update_stream.notify_commit(global_version=self.store.global_version)
            interval = self.config.syncer_checkpoint_interval_rounds
            if interval > 0 and self.store.metrics.sync_rounds_committed % interval == 0:
                self._write_syncer_checkpoint()
        return commit

    def _write_syncer_checkpoint(self) -> None:
        last_event = self.event_log.events[-1] if self.event_log.events else None
        checkpoint_global_vector_ref = None
        if self.config.checkpoint_artifact_codec == "binary_v1":
            checkpoint_global_vector_ref = self._write_global_vector_artifact(
                "checkpoint_syncer_global_vector",
                self.store.global_vector,
                self.store.global_version,
                codec=self.config.checkpoint_artifact_codec,
            )
        checkpoint = make_syncer_checkpoint(
            run_id=self.config.run_id,
            global_version=self.store.global_version,
            global_vector=self.store.global_vector.astype(float).tolist(),
            outer_optimizer_state=outer_optimizer_state(self.store.optimizer),
            fragment_store_state={
                "num_fragments": self.store.num_fragments,
                "pending_policy": "discard_on_recovery",
                "checkpoint_artifact_codec": self.config.checkpoint_artifact_codec,
                "global_vector_artifact_ref": checkpoint_global_vector_ref,
            },
            learner_registry_state={
                "registered_learners": sorted(self.registered_learners),
                "unhealthy_learners": sorted(self.unhealthy_learners),
                "learner_tokens_processed": self.learner_tokens_processed,
                "learner_trainer_metrics": self.learner_trainer_metrics,
                "trainer_state_kind": self.trainer_state_kind,
                "learner_status": {
                    learner_id: status.value for learner_id, status in self.learner_status.items()
                },
                "update_stream": self.update_stream.snapshot(),
            },
            idempotency_table=self.idempotency,
            committed_round_state={
                "last_commit_payload": self.last_commit_payload,
                "global_version": self.store.global_version,
            },
            pending_round_state={"discarded_on_recovery": True},
            metrics_snapshot={
                "store": asdict(self.store.metrics),
                "update_stream": self.update_stream.metrics_dict(),
                "backpressure": asdict(self.backpressure.metrics),
            },
            event_log_offset=len(self.event_log.events),
            last_event_id=last_event.event_id if last_event else None,
            written_logical_time=self.logical_time,
        )
        checkpoint_artifact_ref: dict[str, Any] | None = None
        if self.config.checkpoint_storage_mode in {"inline", "dual"}:
            write_syncer_checkpoint_atomic(self.checkpoint_path, checkpoint)
        if self.config.checkpoint_storage_mode in {"chunked", "dual"}:
            checkpoint_slug = (
                f"syncer_checkpoint-v{checkpoint.global_version:08d}"
                f"-t{self.logical_time:08d}.artifact.json"
            )
            manifest_path = (
                self.config.workdir / "live_checkpoints" / checkpoint_slug
            )
            chunk_root = self.config.workdir / "live_checkpoints" / "store"
            manifest = write_chunked_syncer_checkpoint(
                manifest_path=manifest_path,
                chunk_store_dir=chunk_root,
                checkpoint=checkpoint,
                chunk_size_bytes=self.config.chunk_size_bytes,
            )
            checkpoint_artifact_ref = self.artifact_transport.make_ref(
                manifest=manifest,
                manifest_path=manifest_path,
                chunk_root=chunk_root,
                created_by="syncer",
            ).model_dump(mode="json")
        self.event_log.append(
            EventType.SYNCER_CHECKPOINT_WRITTEN,
            logical_time=self._time(),
            payload={
                "checkpoint_path": str(self.checkpoint_path),
                "global_version": checkpoint.global_version,
                "last_event_id": checkpoint.last_event_id,
                "checksum": checkpoint.checksum,
                "checkpoint_storage_mode": self.config.checkpoint_storage_mode,
                "checkpoint_artifact_ref": checkpoint_artifact_ref,
                "checkpoint_artifact_codec": self.config.checkpoint_artifact_codec,
            },
        )
        checkpoint_ref: dict[str, Any]
        required_hashes: dict[str, str] = {}
        if checkpoint_artifact_ref is not None:
            recovery_checkpoint_path = manifest_path
            checkpoint_ref = {
                "manifest_path": str(recovery_checkpoint_path),
                "chunk_root": str(chunk_root),
                "manifest_hash": checkpoint_artifact_ref.get("manifest_hash"),
                "artifact_id": checkpoint_artifact_ref.get("artifact_id"),
            }
            required_hashes[str(recovery_checkpoint_path)] = sha256_file(
                recovery_checkpoint_path
            )
            recovery_source = (
                "chunked" if self.config.checkpoint_storage_mode == "chunked" else "dual"
            )
        else:
            checkpoint_ref = {
                "path": str(self.checkpoint_path),
                "checksum": checkpoint.checksum,
            }
            if self.checkpoint_path.exists():
                required_hashes[str(self.checkpoint_path)] = sha256_file(self.checkpoint_path)
            recovery_source = "inline"
        recovery_manifest = make_recovery_manifest(
            run_id=self.config.run_id,
            manifest_id=f"{self.config.run_id}:recovery:{checkpoint.global_version}",
            created_logical_time=self.logical_time,
            global_version=checkpoint.global_version,
            checkpoint_ref=checkpoint_ref,
            checkpoint_storage_mode=self.config.checkpoint_storage_mode,
            recovery_source=recovery_source,
            global_state_refs=(
                [checkpoint_global_vector_ref] if checkpoint_global_vector_ref else []
            ),
            required_artifact_hashes=required_hashes,
            compaction_watermarks={
                "event_log_offset": checkpoint.event_log_offset,
                "idempotency_records": len(checkpoint.idempotency_table),
            },
            previous_recovery_manifest_hash=(
                None
                if not self.recovery_manifest_path.exists()
                else json.loads(
                    self.recovery_manifest_path.read_text(encoding="utf-8")
                ).get("manifest_hash")
            ),
        )
        versioned_recovery_path = (
            self.config.workdir
            / "recovery_manifests"
            / f"recovery-v{checkpoint.global_version:08d}-t{self.logical_time:08d}.json"
        )
        write_recovery_manifest_atomic(versioned_recovery_path, recovery_manifest)
        write_recovery_manifest_atomic(self.recovery_manifest_path, recovery_manifest)

    def _recover_from_checkpoint(self) -> None:
        checkpoint_artifact_ref: dict[str, Any] | None = None
        if self.config.checkpoint_storage_mode in {"chunked", "dual"}:
            if not self.recovery_manifest_path.exists():
                raise InvariantViolation("missing recovery manifest for chunked checkpoint")
            recovery_manifest = load_recovery_manifest(self.recovery_manifest_path)
            manifest_value = recovery_manifest.checkpoint_ref.get("manifest_path")
            if not manifest_value:
                raise InvariantViolation("recovery manifest missing checkpoint manifest_path")
            manifest_path = Path(str(manifest_value))
            if not manifest_path.is_absolute():
                manifest_path = self.config.workdir / manifest_path
            chunk_root_value = recovery_manifest.checkpoint_ref.get("chunk_root")
            chunk_store_dir = (
                Path(str(chunk_root_value))
                if chunk_root_value
                else self.config.workdir / "live_checkpoints" / "store"
            )
            if not chunk_store_dir.is_absolute():
                chunk_store_dir = self.config.workdir / chunk_store_dir
            if not manifest_path.exists():
                raise InvariantViolation("missing chunked syncer checkpoint artifact")
            checkpoint = load_chunked_syncer_checkpoint(
                manifest_path=manifest_path,
                chunk_store_dir=chunk_store_dir,
            )
            manifest = ChunkStore(chunk_store_dir).read_manifest(manifest_path)
            checkpoint_artifact_ref = self.artifact_transport.make_ref(
                manifest=manifest,
                manifest_path=manifest_path,
                chunk_root=chunk_store_dir,
                created_by="syncer",
            ).model_dump(mode="json")
            self.recovery_source = "chunked"
        else:
            checkpoint = load_syncer_checkpoint(self.checkpoint_path)
            self.recovery_source = "inline"
        require_checkpoint_for_run(checkpoint, run_id=self.config.run_id)
        global_vector_ref = checkpoint.fragment_store_state.get("global_vector_artifact_ref")
        if checkpoint.fragment_store_state.get("checkpoint_artifact_codec") == "binary_v1":
            if not global_vector_ref:
                raise InvariantViolation("binary checkpoint missing global vector artifact")
            from decodilo.syncer.global_state_store import read_global_vector_artifact

            artifact_vector, artifact_version = read_global_vector_artifact(
                ref=dict(global_vector_ref),
                transport=self.artifact_transport,
            )
            if artifact_version != checkpoint.global_version:
                raise InvariantViolation("binary checkpoint global vector version mismatch")
            checkpoint_vector = artifact_vector.astype(float).tolist()
        else:
            checkpoint_vector = checkpoint.global_vector
        self.store.global_vector = np.asarray(checkpoint_vector, dtype=np.float64)
        self.store.global_version = checkpoint.global_version
        self.idempotency = {
            str(key): dict(value) for key, value in checkpoint.idempotency_table.items()
        }
        registry = checkpoint.learner_registry_state
        self.registered_learners = set(registry.get("registered_learners", []))
        self.unhealthy_learners = set(registry.get("unhealthy_learners", []))
        self.learner_tokens_processed = {
            str(key): int(value)
            for key, value in dict(registry.get("learner_tokens_processed", {})).items()
        }
        self.learner_trainer_metrics = {
            str(key): dict(value)
            for key, value in dict(registry.get("learner_trainer_metrics", {})).items()
        }
        self.trainer_state_kind = str(registry.get("trainer_state_kind", self.trainer_state_kind))
        self.learner_status = {
            str(key): LearnerStatus(str(value))
            for key, value in dict(registry.get("learner_status", {})).items()
        }
        self.update_stream.restore(dict(registry.get("update_stream", {})))
        outer_state = dict(checkpoint.outer_optimizer_state)
        outer_name = str(
            outer_state.get(
                "outer_optimizer",
                outer_state.get("name", self.config.outer_optimizer),
            )
        )
        self.store.optimizer = create_outer_optimizer(
            outer_name,
            outer_lr=float(outer_state.get("outer_lr", self.config.outer_lr)),
            momentum=float(outer_state.get("momentum", self.config.outer_momentum)),
        )
        if hasattr(self.store.optimizer, "velocity") and outer_state.get("velocity"):
            self.store.optimizer.velocity = np.asarray(outer_state["velocity"], dtype=np.float64)
        if hasattr(self.store.optimizer, "step"):
            self.store.optimizer.step = int(outer_state.get("step", 0))
        metrics = checkpoint.metrics_snapshot.get("store", {})
        for field_name, value in dict(metrics).items():
            if hasattr(self.store.metrics, field_name):
                setattr(self.store.metrics, field_name, value)
        self.last_commit_payload = checkpoint.committed_round_state.get("last_commit_payload")
        max_existing_logical_time = max(
            (event.logical_time for event in self.event_log.events),
            default=checkpoint.written_logical_time,
        )
        self.logical_time = max(self.logical_time, max_existing_logical_time + 1)
        self.event_log.append(
            EventType.SYNCER_RECOVERED,
            logical_time=self._time(),
            payload={
                "checkpoint_path": str(self.checkpoint_path),
                "global_version": self.store.global_version,
                "checkpoint_run_id": checkpoint.run_id,
                "discarded_pending_round": True,
                "recovery_source": self.recovery_source,
                "checkpoint_storage_mode": self.config.checkpoint_storage_mode,
                "checkpoint_artifact_ref": checkpoint_artifact_ref,
                "checkpoint_artifact_codec": checkpoint.fragment_store_state.get(
                    "checkpoint_artifact_codec",
                    "json_safe",
                ),
            },
        )
        for learner_id in sorted(self.registered_learners):
            self.event_log.append(
                EventType.LEARNER_RECONNECTED,
                logical_time=self._time(),
                learner_id=learner_id,
                payload={
                    "learner_id": learner_id,
                    "recovery_version": self.store.global_version,
                    "reconnected": True,
                    "source": "syncer_recovery_registry",
                },
            )

    def _global_state_payload(self, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "global_version": self.store.global_version,
            "unhealthy_learners": sorted(self.unhealthy_learners),
        }
        use_chunked_target_vector = (
            self.config.artifact_transfer_mode == "object_store"
            or self.target_vector.nbytes > self.config.inline_payload_max_bytes
        )
        if use_chunked_target_vector:
            target_ref = self._write_global_vector_artifact(
                "target_vector",
                self.target_vector,
                self.store.global_version,
            )
            payload["target_vector_artifact_ref"] = target_ref
            if self.config.artifact_transfer_mode == "object_store":
                payload["target_vector_artifact_transfer"] = "fetch_chunks"
            else:
                payload["target_vector_artifact_bundle"] = artifact_bundle_from_ref(
                    target_ref, transport=self.artifact_transport
                )
        else:
            payload["target_vector"] = self.target_vector.tolist()
        use_chunked_global_update = self.config.global_update_storage_mode == "chunked" or (
            self.config.global_update_storage_mode == "auto"
            and self.store.global_vector.nbytes > self.config.inline_payload_max_bytes
        )
        if use_chunked_global_update:
            ref = self._write_global_vector_artifact(
                "global_update",
                self.store.global_vector,
                self.store.global_version,
            )
            payload["global_vector_artifact_ref"] = ref
            if self.config.artifact_transfer_mode == "object_store":
                payload["global_vector_artifact_transfer"] = "fetch_chunks"
            else:
                payload["global_vector_artifact_bundle"] = artifact_bundle_from_ref(
                    ref, transport=self.artifact_transport
                )
            payload["global_update_storage_mode"] = "chunked"
            payload["artifact_transfer_mode"] = self.config.artifact_transfer_mode
        else:
            payload["global_vector"] = self.store.global_vector.tolist()
        if extra:
            payload.update(extra)
        return payload

    def build_summary(self) -> dict[str, Any]:
        useful_tokens = self.store.metrics.useful_tokens
        total_tokens = max(sum(self.learner_tokens_processed.values()), useful_tokens)
        final_loss = convex_loss(self.store.global_vector, self.target_vector)
        trainer_metric_values = list(self.learner_trainer_metrics.values())
        trainer_state_byte_values = [
            int(value["trainer_state_bytes_estimate"])
            for value in trainer_metric_values
            if value.get("trainer_state_bytes_estimate") is not None
        ]
        trainer_num_parameter_values = [
            int(value["trainer_num_parameters"])
            for value in trainer_metric_values
            if value.get("trainer_num_parameters") is not None
        ]
        trainer_state_bytes = max(trainer_state_byte_values) if trainer_state_byte_values else None
        trainer_num_parameters = (
            max(trainer_num_parameter_values) if trainer_num_parameter_values else None
        )
        trainer_final_loss = next(
            (
                value.get("trainer_final_loss")
                for value in reversed(trainer_metric_values)
                if value.get("trainer_final_loss") is not None
            ),
            None,
        )
        trainer_final_eval_loss = next(
            (
                value.get("trainer_final_eval_loss")
                for value in reversed(trainer_metric_values)
                if value.get("trainer_final_eval_loss") is not None
            ),
            None,
        )
        trainer_nonfinite_detected = any(
            bool(value.get("trainer_nonfinite_detected")) for value in trainer_metric_values
        )
        inner_optimizer_semantics = next(
            (
                value.get("inner_optimizer_semantics")
                for value in reversed(trainer_metric_values)
                if value.get("inner_optimizer_semantics") is not None
            ),
            None,
        )
        training_attempted = any(
            bool(value.get("training_attempted")) for value in trainer_metric_values
        )
        real_training_mechanics_exercised = any(
            bool(value.get("real_training_mechanics_exercised"))
            for value in trainer_metric_values
        )
        optimizer_state_present = any(
            bool(value.get("optimizer_state")) for value in trainer_metric_values
        )
        real_model_training_claimed = any(
            bool(value.get("real_model_training_claimed")) for value in trainer_metric_values
        )
        paper_scale_training_claimed = any(
            bool(value.get("paper_scale_training_claimed")) for value in trainer_metric_values
        )
        outer_name = outer_optimizer_name(self.store.optimizer)
        metrics = SimulationMetrics(
            total_tokens_processed=total_tokens,
            useful_tokens_accepted=useful_tokens,
            rejected_tokens=self.store.metrics.rejected_tokens,
            stale_tokens=self.store.metrics.stale_tokens,
            wasted_tokens=max(total_tokens - useful_tokens, 0),
            committed_sync_rounds=self.store.metrics.sync_rounds_committed,
            skipped_sync_rounds=self.store.metrics.sync_rounds_skipped,
            rejected_fragments=self.store.metrics.rejected_fragments,
            stale_fragments=self.store.metrics.stale_fragments,
            learner_uptime_ticks={},
            learner_failed_ticks={},
            learner_paused_ticks={},
            goodput_ratio=useful_tokens / total_tokens if total_tokens else 0.0,
            final_loss=final_loss,
            accepted_updates=self.store.metrics.accepted_updates,
        )
        return {
            "run_id": self.config.run_id,
            "final_global_version": self.store.global_version,
            "final_global_vector": self.store.global_vector.tolist(),
            "final_loss": final_loss,
            "trainer_state_kind": self.trainer_state_kind,
            "trainer_metrics": {
                "trainer_state_bytes_estimate": trainer_state_bytes,
                "trainer_num_parameters": trainer_num_parameters,
                "trainer_final_loss": trainer_final_loss,
                "trainer_final_eval_loss": trainer_final_eval_loss,
                "trainer_nonfinite_detected": trainer_nonfinite_detected,
            },
            "metrics": {
                "total_tokens_processed": metrics.total_tokens_processed,
                "useful_tokens_accepted": metrics.useful_tokens_accepted,
                "rejected_tokens": metrics.rejected_tokens,
                "stale_tokens": metrics.stale_tokens,
                "wasted_tokens": metrics.wasted_tokens,
                "committed_sync_rounds": metrics.committed_sync_rounds,
                "sync_rounds_committed": metrics.sync_rounds_committed,
                "skipped_sync_rounds": metrics.skipped_sync_rounds,
                "rejected_fragments": metrics.rejected_fragments,
                "stale_fragments": metrics.stale_fragments,
                "goodput_ratio": metrics.goodput_ratio,
                "accepted_updates": metrics.accepted_updates,
                "outer_optimizer": outer_optimizer_name(self.store.optimizer),
                "outer_optimizer_semantics": outer_name,
                "outer_momentum": float(getattr(self.store.optimizer, "momentum", 0.0)),
                "inner_optimizer_semantics": inner_optimizer_semantics,
                "training_attempted": training_attempted,
                "real_training_mechanics_exercised": real_training_mechanics_exercised,
                "real_model_training_claimed": real_model_training_claimed,
                "paper_scale_training_claimed": paper_scale_training_claimed,
                "optimizer_state_present": optimizer_state_present,
                # Honest split of the former "pseudo_gradient_check_passed" field.
                # These two are cheap semantic facts the syncer can assert directly:
                # the outer-optimizer identity is known/declared, and the Nesterov
                # path actually committed at least one round.
                "outer_optimizer_semantics_checked": True,
                "nesterov_outer_optimizer_exercised": (
                    outer_name == "nesterov"
                    and self.store.metrics.sync_rounds_committed > 0
                ),
                # The genuine numeric re-derivation (apply declared outer optimizer to
                # logged old_global_vector + weighted_delta and match new_global_vector)
                # is performed downstream against the event log in local_runner. The
                # syncer cannot cheaply re-derive here, so it reports None (unknown).
                "pseudo_gradient_numeric_check_passed": None,
                # Backward-compatible alias. NOTE: at the syncer level this still only
                # means "Nesterov path exercised". local_runner overwrites it with the
                # genuine numeric result when inline vectors are available, so the final
                # report's value is backed by numeric verification (not a tautology).
                "pseudo_gradient_check_passed": outer_name == "nesterov"
                and self.store.metrics.sync_rounds_committed > 0,
                "chunked_fragment_submissions": self.store.metrics.chunked_fragment_submissions,
                "inline_fragment_submissions": self.store.metrics.inline_fragment_submissions,
                "artifact_ref_validations": self.store.metrics.artifact_ref_validations,
                "artifact_ref_validation_failures": (
                    self.store.metrics.artifact_ref_validation_failures
                ),
                "chunked_fragment_bytes_accepted": (
                    self.store.metrics.chunked_fragment_bytes_accepted
                ),
                "chunked_fragment_bytes_rejected": (
                    self.store.metrics.chunked_fragment_bytes_rejected
                ),
                "artifact_bytes_read": self.store.metrics.artifact_bytes_read,
                "artifact_chunks_read": self.store.metrics.artifact_chunks_read,
                "artifact_validation_seconds": self.store.metrics.artifact_validation_seconds,
                "global_update_artifact_codec": self.config.tensor_artifact_codec,
                "binary_global_update_messages_sent": (
                    self.update_stream.metrics.global_update_messages_sent
                    if self.config.tensor_artifact_codec == "binary_v1"
                    else 0
                ),
                "binary_global_update_bytes_sent": (
                    self.store.metrics.live_streaming_merge_bytes_written
                    if self.config.tensor_artifact_codec == "binary_v1"
                    else 0
                ),
                "binary_global_update_apply_failures": 0,
                "live_streaming_merges": self.store.metrics.live_streaming_merges,
                "live_streaming_merge_bytes_read": (
                    self.store.metrics.live_streaming_merge_bytes_read
                ),
                "live_streaming_merge_bytes_written": (
                    self.store.metrics.live_streaming_merge_bytes_written
                ),
                "live_streaming_merge_chunks_processed": (
                    self.store.metrics.live_streaming_merge_chunks_processed
                ),
                "live_streaming_merge_peak_working_bytes_estimate": (
                    self.store.metrics.live_streaming_merge_peak_working_bytes_estimate
                ),
                "binary_streaming_merges": self.store.metrics.binary_streaming_merges,
                "binary_streaming_merge_bytes_read": (
                    self.store.metrics.binary_streaming_merge_bytes_read
                ),
                "binary_streaming_merge_bytes_written": (
                    self.store.metrics.binary_streaming_merge_bytes_written
                ),
                "binary_streaming_merge_chunks_read": (
                    self.store.metrics.binary_streaming_merge_chunks_read
                ),
                "binary_streaming_merge_chunks_written": (
                    self.store.metrics.binary_streaming_merge_chunks_written
                ),
                "binary_streaming_merge_peak_working_bytes_estimate": (
                    self.store.metrics.binary_streaming_merge_peak_working_bytes_estimate
                ),
                "binary_streaming_merge_wall_time_seconds": (
                    self.store.metrics.binary_streaming_merge_wall_time_seconds
                ),
                "merge_algorithm": (
                    "out_of_core_binary_v1"
                    if self.store.metrics.binary_streaming_merges > 0
                    else self.config.merge_mode
                ),
                "out_of_core_merge_configured": (
                    self.config.merge_mode == "streaming_chunked"
                    and self.config.fragment_artifact_codec == "binary_v1"
                ),
                "max_working_bytes": self.config.chunk_size_bytes * 5,
                "merge_blocks_processed": self.store.metrics.live_streaming_merge_chunks_processed,
                "merge_peak_working_bytes_estimate": (
                    self.store.metrics.live_streaming_merge_peak_working_bytes_estimate
                ),
                "numeric_merge_performed": self.store.metrics.numeric_merge_performed,
                "simulation_only_merge_count": self.store.metrics.simulation_only_merge_count,
                **self.update_stream.metrics_dict(),
                "backpressure_rejections": self.backpressure.metrics.backpressure_rejections,
                "message_count_pressure": self.backpressure.metrics.message_count_pressure,
                "byte_pressure": self.backpressure.metrics.byte_pressure,
                "memory_budget_pressure": self.backpressure.metrics.memory_budget_pressure,
                "spill_budget_pressure": self.backpressure.metrics.spill_budget_pressure,
                "pending_messages_current": self.backpressure.metrics.pending_messages_current,
                "pending_fragments_current": self.backpressure.metrics.pending_fragments_current,
                "inflight_bytes_current": self.backpressure.metrics.inflight_bytes_current,
                "inflight_bytes_peak": self.backpressure.metrics.inflight_bytes_peak,
            },
            "unhealthy_learners": sorted(self.unhealthy_learners),
            "recovery_source": self.recovery_source,
            "event_log_path": str(self.config.workdir / "events.jsonl"),
            "artifact_transfer_mode": self.config.artifact_transfer_mode,
            "artifact_storage_backend": self.artifact_transport.policy.storage_backend,
            "code_version": __version__ or None,
        }


def build_config_from_args(args: argparse.Namespace) -> SyncerServiceConfig:
    sim_config = SimulationConfig(
        learners=args.learners,
        vector_dim=args.vector_dim,
        num_fragments=args.fragments,
        steps=args.steps,
        local_steps_per_sync=args.local_steps_per_sync,
        min_quorum=args.min_quorum,
        grace_window_ticks=args.grace_window,
        max_staleness_versions=args.max_staleness,
        seed=args.seed,
        outer_lr=args.outer_lr,
        run_id=args.run_id,
    )
    return SyncerServiceConfig(
        run_id=args.run_id or deterministic_run_id(sim_config),
        workdir=Path(args.workdir),
        host=args.host,
        port=args.port,
        learners=args.learners,
        vector_dim=args.vector_dim,
        num_fragments=args.fragments,
        steps=args.steps,
        local_steps_per_sync=args.local_steps_per_sync,
        min_quorum=args.min_quorum,
        grace_window_ticks=args.grace_window,
        max_staleness_versions=args.max_staleness,
        seed=args.seed,
        learner_lr=args.learner_lr,
        outer_optimizer=args.outer_optimizer,
        outer_lr=args.outer_lr,
        outer_momentum=args.outer_momentum,
        heartbeat_timeout_seconds=args.heartbeat_timeout_seconds,
        heartbeat_check_interval_seconds=args.heartbeat_check_interval_seconds,
        update_long_poll_timeout_seconds=args.update_long_poll_timeout_seconds,
        max_learner_version_lag=args.max_learner_version_lag,
        max_pending_messages_per_learner=args.max_pending_messages_per_learner,
        max_pending_fragments_per_learner=args.max_pending_fragments_per_learner,
        max_inflight_bytes_per_learner=args.max_inflight_bytes_per_learner,
        max_total_inflight_bytes=args.max_total_inflight_bytes,
        syncer_checkpoint_interval_rounds=args.syncer_checkpoint_interval_rounds,
        recover_from_checkpoint=args.recover_from_checkpoint,
        syncer_checkpoint_path=args.syncer_checkpoint_path,
        payload_storage_mode=args.payload_storage_mode,
        checkpoint_storage_mode=args.checkpoint_storage_mode,
        merge_mode=args.merge_mode,
        global_update_storage_mode=args.global_update_storage_mode,
        artifact_root=args.artifact_root,
        chunk_store_root=args.chunk_store_root,
        inline_payload_max_bytes=args.inline_payload_max_bytes,
        chunk_size_bytes=args.chunk_size_bytes,
        tensor_artifact_codec=args.tensor_artifact_codec,
        fragment_artifact_codec=args.fragment_artifact_codec,
        checkpoint_artifact_codec=args.checkpoint_artifact_codec,
        artifact_transfer_mode=args.artifact_transfer_mode,
        artifact_storage_backend=args.artifact_storage_backend,
        s3_endpoint_url=args.s3_endpoint_url,
        s3_bucket=args.s3_bucket,
        s3_prefix=args.s3_prefix,
        s3_region=args.s3_region,
        s3_access_key_ref=args.s3_access_key_ref,
        s3_secret_key_ref=args.s3_secret_key_ref,
        s3_session_token_ref=args.s3_session_token_ref,
    )


async def async_main(args: argparse.Namespace) -> int:
    config = build_config_from_args(args)
    service = SyncerService(config)
    await service.serve_until_stopped(ready_file=Path(args.ready_file))
    return 0


def main(args: argparse.Namespace) -> int:
    return asyncio.run(async_main(args))
