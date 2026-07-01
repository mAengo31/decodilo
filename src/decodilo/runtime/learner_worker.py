"""Learner worker process for the local multiprocessing runtime."""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from decodilo.runtime.artifact_transport import ArtifactTransportPolicy, LocalArtifactTransport
from decodilo.runtime.chunked_payloads import default_artifact_root, default_chunk_store_root
from decodilo.runtime.chunked_runtime_modes import should_use_chunked_payload
from decodilo.runtime.chunked_update_delivery import apply_update_ref_to_vector
from decodilo.runtime.learner_checkpoint import (
    load_checkpoint,
    make_checkpoint,
    write_checkpoint_atomic,
)
from decodilo.runtime.remote_artifact_fetch import (
    artifact_bundle_from_ref,
    materialize_artifact_bundle,
    materialize_artifact_chunk_upload,
)
from decodilo.trainer.fragment_artifacts import write_fragment_artifact
from decodilo.trainer.interface import TrainerAdapter
from decodilo.trainer.registry import create_trainer
from decodilo.trainer.state import TrainerConfig, TrainerState
from decodilo.trainer.state_codec import decode_state, make_fragment, validate_fragment
from decodilo.transport.envelope import MessageType, make_envelope
from decodilo.transport.tcp_client import JsonlTcpClient


class LearnerWorker:
    """Connects one fake learner process to the syncer service."""

    def __init__(
        self,
        *,
        learner_id: str,
        run_id: str,
        host: str,
        port: int,
        workdir: Path,
        steps: int,
        local_steps_per_sync: int,
        heartbeat_interval_seconds: float,
        step_delay_seconds: float,
        learner_lr: float,
        slow_factor: float = 1.0,
        trainer_type: str = "numpy_convex",
        trainer_config: dict[str, Any] | None = None,
        seed: int = 123,
        payload_storage_mode: str = "inline",
        global_update_storage_mode: str = "inline",
        artifact_root: Path | None = None,
        chunk_store_root: Path | None = None,
        inline_payload_max_bytes: int = 1_000_000,
        chunk_size_bytes: int = 1024 * 1024,
        fragment_artifact_codec: str = "json_safe",
        tensor_artifact_codec: str = "json_safe",
        checkpoint_artifact_codec: str = "json_safe",
        artifact_transfer_mode: str = "bundle",
    ) -> None:
        self.learner_id = learner_id
        self.run_id = run_id
        self.host = host
        self.port = port
        self.workdir = workdir
        self.steps = steps
        self.local_steps_per_sync = local_steps_per_sync
        self.heartbeat_interval_seconds = heartbeat_interval_seconds
        self.step_delay_seconds = step_delay_seconds
        self.learner_lr = learner_lr
        self.slow_factor = slow_factor
        self.trainer_type = trainer_type
        self.trainer_config = trainer_config or {}
        self.seed = seed
        self.payload_storage_mode = payload_storage_mode
        self.global_update_storage_mode = global_update_storage_mode
        self.artifact_root = artifact_root or default_artifact_root(workdir)
        self.chunk_store_root = chunk_store_root or default_chunk_store_root(workdir)
        self.inline_payload_max_bytes = inline_payload_max_bytes
        self.chunk_size_bytes = chunk_size_bytes
        self.fragment_artifact_codec = fragment_artifact_codec
        self.tensor_artifact_codec = tensor_artifact_codec
        self.checkpoint_artifact_codec = checkpoint_artifact_codec
        self.artifact_transfer_mode = artifact_transfer_mode
        self.artifact_transport = LocalArtifactTransport(
            policy=ArtifactTransportPolicy(
                workdir=str(workdir),
                artifact_root=str(self.artifact_root),
                storage_backend=(
                    "syncer_object_store"
                    if artifact_transfer_mode == "object_store"
                    else "local_filesystem"
                ),
            )
        )
        self.log_path = workdir / f"{learner_id}.log"
        self.checkpoint_path = workdir / f"{learner_id}.checkpoint.json"
        self.control_path = workdir / f"{learner_id}.control.json"
        self.request_timeout_seconds = (
            60.0
            if payload_storage_mode == "chunked" or global_update_storage_mode == "chunked"
            else 2.0
        )
        self.client = JsonlTcpClient(
            host=host, port=port, timeout_seconds=self.request_timeout_seconds
        )
        self.trainer: TrainerAdapter | None = None
        self.baseline_throughput_tokens_per_step = (
            100 + int(self.learner_id.rsplit("-", 1)[-1]) * 10
        )
        self.in_flight_idempotency_key: str | None = None
        self.last_control_sequence = -1
        self.pending_control_event: dict[str, Any] | None = None
        self.force_submit_after_register = False

    def _log(self, event_type: str, payload: dict[str, Any] | None = None) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "event_type": event_type,
                        "learner_id": self.learner_id,
                        "payload": payload or {},
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    async def run(self) -> int:
        self._log("starting")
        await self.client.connect()
        try:
            await self._register()
            await self._training_loop()
            await self._shutdown()
            self._log("finished")
            return 0
        finally:
            await self.client.close()

    async def _request(self, envelope, *, allow_reconnect: bool = True):
        try:
            return await self.client.request(envelope)
        except Exception:
            if not allow_reconnect:
                raise
            await self._reconnect()
            return await self.client.request(envelope)

    async def _reconnect(self) -> None:
        ready_path = self.workdir / "syncer_ready.json"
        deadline = time.monotonic() + 15.0
        last_error: Exception | None = None
        await self.client.close()
        while time.monotonic() < deadline:
            if ready_path.exists():
                ready = json.loads(ready_path.read_text(encoding="utf-8"))
                self.host = str(ready["host"])
                self.port = int(ready["port"])
            self.client = JsonlTcpClient(
                host=self.host,
                port=self.port,
                timeout_seconds=self.request_timeout_seconds,
            )
            try:
                await self.client.connect()
                break
            except OSError as exc:
                last_error = exc
                await asyncio.sleep(0.05)
        else:
            raise RuntimeError(f"learner reconnect failed: {last_error}")
        self._log("reconnected", {"host": self.host, "port": self.port})
        await self._register(reconnected=True)

    async def _register(self, *, reconnected: bool = False) -> None:
        response = await self._request(
            make_envelope(
                run_id=self.run_id,
                sender_id=self.learner_id,
                recipient_id="syncer",
                message_type=MessageType.REGISTER_LEARNER,
                payload={"learner_id": self.learner_id, "reconnected": reconnected},
            ),
            allow_reconnect=False,
        )
        if response.message_type != MessageType.REGISTER_LEARNER_ACK:
            raise RuntimeError(f"registration failed: {response.payload}")
        if "global_vector_artifact_ref" in response.payload:
            global_vector, response_version = await self._apply_update_ref_to_vector(
                response.payload["global_vector_artifact_ref"]
            )
        else:
            global_vector = np.asarray(response.payload["global_vector"], dtype=np.float64)
            response_version = int(response.payload["global_version"])
        target_vector = np.asarray(response.payload["target_vector"], dtype=np.float64)
        checkpoint = None
        initial_state: TrainerState | None = None
        if self.checkpoint_path.exists():
            checkpoint = load_checkpoint(self.checkpoint_path)
            self.force_submit_after_register = True
            if checkpoint.trainer_payload.get("trainer_state"):
                initial_state = decode_state(str(checkpoint.trainer_payload["trainer_state"]))
            self._log(
                "checkpoint_loaded",
                {
                    "local_step": checkpoint.local_step,
                    "last_global_version_seen": checkpoint.last_global_version_seen,
                },
            )
        trainer_type = checkpoint.trainer_type if checkpoint else self.trainer_type
        self.trainer = create_trainer(trainer_type)
        throughput = (
            checkpoint.throughput_tokens_per_step
            if checkpoint
            else self.baseline_throughput_tokens_per_step
        )
        trainer_config_payload = {
            "vector_dim": int(global_vector.size),
            "learning_rate": self.learner_lr,
            "throughput_tokens_per_step": throughput,
            "target_vector": target_vector.astype(float).tolist(),
            "initial_vector": (
                np.asarray(checkpoint.parameter_vector, dtype=np.float64).astype(float).tolist()
                if checkpoint and initial_state is None
                else global_vector.astype(float).tolist()
            ),
            **self.trainer_config,
        }
        self.trainer.initialize(
            run_id=self.run_id,
            learner_id=self.learner_id,
            seed=self.seed,
            initial_state=initial_state,
            config=TrainerConfig.model_validate(trainer_config_payload),
        )
        if response_version > self.trainer.health().global_version:
            self._apply_global_vector(global_vector, global_version=response_version)
        if self.slow_factor != 1.0:
            self._slow_trainer(self.slow_factor)
        self._log(
            "registered",
            {
                "global_version": self.trainer.health().global_version,
                "slow_factor": self.slow_factor,
                "trainer_type": trainer_type,
                "reconnected": reconnected,
            },
        )
        await self._ack_update_if_needed()
        self._write_checkpoint()

    async def _training_loop(self) -> None:
        assert self.trainer is not None
        last_heartbeat = 0.0
        for _ in range(self.steps):
            await self._apply_control_if_present()
            self.trainer.train_local_steps(1)
            now = time.monotonic()
            if now - last_heartbeat >= self.heartbeat_interval_seconds:
                await self._heartbeat()
                last_heartbeat = now
            health = self.trainer.health()
            if (
                health.local_step > 0
                and (
                    health.local_step % self.local_steps_per_sync == 0
                    or self.force_submit_after_register
                )
                and health.tokens_since_last_sync > 0
                and self.in_flight_idempotency_key is None
            ):
                await self._submit_fragment()
                self.force_submit_after_register = False
            await asyncio.sleep(self.step_delay_seconds)

    async def _heartbeat(self) -> None:
        assert self.trainer is not None
        health = self.trainer.health()
        state_metadata = self.trainer.get_full_state().metadata
        payload = {
            "local_step": health.local_step,
            "tokens_processed": health.tokens_processed,
            "last_global_version_seen": health.global_version,
            "status": health.status,
            "trainer_state_checksum": health.state_checksum,
            "trainer_state_bytes_estimate": health.state_bytes_estimate,
            "trainer_num_parameters": health.num_parameters,
            "trainer_final_loss": health.final_loss,
            "trainer_final_eval_loss": health.final_eval_loss,
            "trainer_nonfinite_detected": health.nonfinite_detected,
        }
        if state_metadata.get("optimizer") == "adamw":
            payload.update(
                {
                    "inner_optimizer": "adamw",
                    "inner_optimizer_semantics": "adamw",
                    "training_attempted": bool(health.local_step > 0),
                    "real_training_mechanics_exercised": bool(
                        state_metadata.get("real_training_mechanics_exercised", False)
                    ),
                    "real_model_training_claimed": bool(
                        state_metadata.get("real_model_training_claimed", False)
                    ),
                    "paper_scale_training_claimed": bool(
                        state_metadata.get("paper_scale_training_claimed", False)
                    ),
                    "optimizer_state": state_metadata.get("optimizer_state", {}),
                }
            )
        if self.pending_control_event is not None:
            payload.update(self.pending_control_event)
            self.pending_control_event = None
        response = await self._request(
            make_envelope(
                run_id=self.run_id,
                sender_id=self.learner_id,
                recipient_id="syncer",
                message_type=MessageType.HEARTBEAT,
                payload=payload,
            )
        )
        await self._handle_global_payload(response.payload)
        await self._ack_update_if_needed()
        await self._poll_update(timeout_expected=True)
        self._write_checkpoint()

    async def _submit_fragment(self) -> None:
        assert self.trainer is not None
        state = self.trainer.get_full_state()
        fragments = self.trainer.get_state_fragments()
        if not fragments:
            return
        fragment = fragments[0]
        validate_fragment(fragment)
        key = (
            f"{self.run_id}:{self.learner_id}:"
            f"step-{state.local_step}:v-{state.global_version}"
        )
        self.in_flight_idempotency_key = key
        payload = {
            "vector": fragment.data,
            "global_version_seen": fragment.global_version,
            "tokens": fragment.tokens,
            "tokens_processed": state.tokens_processed,
            "local_step": state.local_step,
            "trainer_state_checksum": state.checksum,
            "trainer_state_kind": state.trainer_state_kind,
            "trainer_fragment": fragment.model_dump(mode="json"),
            "tensor_manifest": state.tensor_manifest,
            "flat_state_checksum": state.flat_state_checksum,
            "named_state_checksum": state.named_state_checksum,
        }
        if state.metadata.get("optimizer") == "adamw":
            payload.update(
                {
                    "inner_optimizer": "adamw",
                    "inner_optimizer_semantics": "adamw",
                    "training_attempted": True,
                    "real_training_mechanics_exercised": True,
                    "real_model_training_claimed": bool(
                        state.metadata.get("real_model_training_claimed", False)
                    ),
                    "paper_scale_training_claimed": bool(
                        state.metadata.get("paper_scale_training_claimed", False)
                    ),
                    "optimizer_state": state.metadata.get("optimizer_state", {}),
                }
            )
        inline_payload_bytes = len(json.dumps(payload, sort_keys=True).encode("utf-8"))
        if should_use_chunked_payload(
            mode=self.payload_storage_mode,
            payload_bytes=inline_payload_bytes,
            inline_payload_max_bytes=self.inline_payload_max_bytes,
        ):
            manifest_path = (
                self.artifact_root
                / self.learner_id
                / f"fragment-step-{state.local_step}-v{state.global_version}.artifact.json"
            )
            ref = write_fragment_artifact(
                fragment=fragment,
                transport=self.artifact_transport,
                manifest_path=manifest_path,
                chunk_root=self.chunk_store_root,
                chunk_size_bytes=self.chunk_size_bytes,
                created_by=self.learner_id,
                codec=self.fragment_artifact_codec,
                inline_payload_max_bytes=self.inline_payload_max_bytes,
            )
            payload = {
                "global_version_seen": fragment.global_version,
                "tokens": fragment.tokens,
                "tokens_processed": state.tokens_processed,
                "local_step": state.local_step,
                "trainer_state_checksum": state.checksum,
                "trainer_state_kind": state.trainer_state_kind,
                "trainer_fragment_artifact_ref": ref.model_dump(mode="json"),
                "storage_kind": "artifact_ref",
                "artifact_transfer_mode": self.artifact_transfer_mode,
                "payload_bytes": ref.total_bytes,
                "checksum": fragment.checksum,
                "dtype": fragment.dtype,
                "shape": fragment.shape,
            }
            if self.artifact_transfer_mode == "object_store":
                await self._upload_artifact_ref_to_syncer(ref.model_dump(mode="json"))
            else:
                payload["trainer_fragment_artifact_bundle"] = artifact_bundle_from_ref(
                    ref, transport=self.artifact_transport
                )
            payload["payload_bytes"] = max(
                ref.total_bytes,
                len(json.dumps(payload, sort_keys=True).encode("utf-8")),
            )
        else:
            payload["payload_bytes"] = inline_payload_bytes
        response = await self._request(
            make_envelope(
                run_id=self.run_id,
                sender_id=self.learner_id,
                recipient_id="syncer",
                message_type=MessageType.SUBMIT_FRAGMENT,
                idempotency_key=key,
                payload=payload,
            )
        )
        if response.message_type == MessageType.SUBMIT_FRAGMENT_REJECTED:
            self.in_flight_idempotency_key = None
        await self._handle_global_payload(response.payload)
        await self._ack_update_if_needed()
        self._write_checkpoint()
        self._log(
            "submitted_fragment",
            {
                "idempotency_key": key,
                "response_type": response.message_type.value,
                "outcome": response.payload.get("outcome"),
                "response_payload": response.payload,
            },
        )

    async def _poll_update(self, *, timeout_expected: bool) -> None:
        assert self.trainer is not None
        response = await self._request(
            make_envelope(
                run_id=self.run_id,
                sender_id=self.learner_id,
                recipient_id="syncer",
                message_type=MessageType.SUBSCRIBE_UPDATES,
                payload={
                    "last_applied_global_version": self.trainer.health().global_version,
                    "timeout_expected": timeout_expected,
                },
            )
        )
        if response.message_type == MessageType.GLOBAL_UPDATE_PAYLOAD:
            await self._handle_global_payload(response.payload)
            await self._ack_update_if_needed()
            self._write_checkpoint()

    async def _ack_update_if_needed(self) -> None:
        assert self.trainer is not None
        await self._request(
            make_envelope(
                run_id=self.run_id,
                sender_id=self.learner_id,
                recipient_id="syncer",
                message_type=MessageType.GLOBAL_UPDATE_ACK,
                payload={"global_version": self.trainer.health().global_version},
            )
        )

    async def _apply_control_if_present(self) -> None:
        assert self.trainer is not None
        if not self.control_path.exists():
            return
        try:
            control = json.loads(self.control_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        sequence = int(control.get("sequence", -1))
        if sequence <= self.last_control_sequence:
            return
        self.last_control_sequence = sequence
        if "slow_factor" in control:
            factor = float(control["slow_factor"])
            self._slow_trainer(factor)
            self.pending_control_event = {"control_event": "learner_slowed", "factor": factor}
            self._log("learner_slowed", {"factor": factor})
            await self._heartbeat()
        elif control.get("restore"):
            self._restore_trainer_speed()
            self.pending_control_event = {"control_event": "learner_speed_restored"}
            self._log("learner_speed_restored")
            await self._heartbeat()

    def _write_checkpoint(self) -> None:
        assert self.trainer is not None
        state = self.trainer.get_full_state()
        checkpoint = make_checkpoint(
            run_id=self.run_id,
            learner_id=self.learner_id,
            local_step=state.local_step,
            tokens_processed=state.tokens_processed,
            tokens_since_last_sync=state.tokens_since_last_sync,
            last_global_version_seen=state.global_version,
            last_applied_global_version=state.global_version,
            throughput_tokens_per_step=int(
                state.metadata.get(
                    "throughput_tokens_per_step",
                    self.baseline_throughput_tokens_per_step,
                )
            ),
            parameter_vector=state.parameters,
            trainer_type=state.trainer_type,
            trainer_payload=self.trainer.checkpoint_payload(),
            written_logical_time=state.local_step,
        )
        write_checkpoint_atomic(self.checkpoint_path, checkpoint)

    async def _upload_artifact_ref_to_syncer(self, ref: dict[str, Any]) -> None:
        bundle = artifact_bundle_from_ref(ref, transport=self.artifact_transport)
        chunks = list(bundle.get("chunks") or [])
        for index, chunk in enumerate(chunks):
            response = await self._request(
                make_envelope(
                    run_id=self.run_id,
                    sender_id=self.learner_id,
                    recipient_id="syncer",
                    message_type=MessageType.UPLOAD_ARTIFACT_CHUNK,
                    payload={
                        "artifact_ref": bundle["artifact_ref"],
                        "manifest": bundle["manifest"],
                        "chunk": chunk,
                        "chunk_index": index,
                        "total_chunks": len(chunks),
                        "final": index == len(chunks) - 1,
                    },
                )
            )
            if response.message_type != MessageType.UPLOAD_ARTIFACT_CHUNK_ACK:
                raise RuntimeError(f"artifact upload failed: {response.payload}")
            if index == len(chunks) - 1 and not response.payload.get("complete"):
                raise RuntimeError("artifact upload did not complete")

    async def _fetch_artifact_ref_from_syncer(self, ref: dict[str, Any]) -> None:
        response = await self._request(
            make_envelope(
                run_id=self.run_id,
                sender_id=self.learner_id,
                recipient_id="syncer",
                message_type=MessageType.FETCH_ARTIFACT,
                payload={"artifact_ref": ref, "response_mode": "metadata_only"},
            )
        )
        if response.message_type != MessageType.FETCH_ARTIFACT_RESPONSE:
            raise RuntimeError(f"artifact metadata fetch failed: {response.payload}")
        metadata = response.payload
        chunks = list(metadata.get("chunks") or [])
        for index, chunk_meta in enumerate(chunks):
            chunk_response = await self._request(
                make_envelope(
                    run_id=self.run_id,
                    sender_id=self.learner_id,
                    recipient_id="syncer",
                    message_type=MessageType.FETCH_ARTIFACT_CHUNK,
                    payload={
                        "artifact_ref": metadata["artifact_ref"],
                        "sha256": chunk_meta["sha256"],
                    },
                )
            )
            if chunk_response.message_type != MessageType.FETCH_ARTIFACT_CHUNK_RESPONSE:
                raise RuntimeError(f"artifact chunk fetch failed: {chunk_response.payload}")
            materialize_artifact_chunk_upload(
                {
                    "artifact_ref": metadata["artifact_ref"],
                    "manifest": metadata["manifest"],
                    "chunk": chunk_response.payload,
                    "final": index == len(chunks) - 1,
                },
                transport=self.artifact_transport,
            )

    async def _apply_update_ref_to_vector(self, ref: dict[str, Any]) -> tuple[np.ndarray, int]:
        try:
            return apply_update_ref_to_vector(ref=ref, transport=self.artifact_transport)
        except Exception as exc:
            if self.artifact_transfer_mode == "object_store":
                await self._fetch_artifact_ref_from_syncer(ref)
            else:
                response = await self._request(
                    make_envelope(
                        run_id=self.run_id,
                        sender_id=self.learner_id,
                        recipient_id="syncer",
                        message_type=MessageType.FETCH_ARTIFACT,
                        payload={"artifact_ref": ref},
                    )
                )
                if response.message_type != MessageType.FETCH_ARTIFACT_RESPONSE:
                    raise RuntimeError(f"artifact fetch failed: {response.payload}") from exc
                materialize_artifact_bundle(response.payload, transport=self.artifact_transport)
            return apply_update_ref_to_vector(ref=ref, transport=self.artifact_transport)

    async def _handle_global_payload(self, payload: dict[str, Any]) -> None:
        assert self.trainer is not None
        last_commit = payload.get("last_commit") or payload.get("commit")
        if (
            last_commit
            and self.in_flight_idempotency_key is not None
            and self.learner_id in last_commit.get("accepted_learner_ids", [])
        ):
            if hasattr(self.trainer, "mark_update_accepted"):
                self.trainer.mark_update_accepted()
            self.in_flight_idempotency_key = None
        global_version = payload.get("global_version")
        global_vector = payload.get("global_vector")
        global_vector_ref = payload.get("global_vector_artifact_ref")
        global_vector_bundle = payload.get("global_vector_artifact_bundle")
        if global_version is not None and global_vector_ref is not None:
            if global_vector_bundle is not None:
                materialize_artifact_bundle(global_vector_bundle, transport=self.artifact_transport)
            vector, artifact_version = await self._apply_update_ref_to_vector(global_vector_ref)
            if artifact_version != int(global_version):
                raise RuntimeError("global update artifact version mismatch")
            if int(global_version) > self.trainer.health().global_version:
                self._apply_global_vector(vector, global_version=int(global_version))
                self.in_flight_idempotency_key = None
        elif global_version is not None and global_vector is not None:
            if int(global_version) > self.trainer.health().global_version:
                self._apply_global_vector(
                    np.asarray(global_vector, dtype=np.float64),
                    global_version=int(global_version),
                )
                self.in_flight_idempotency_key = None

    def _apply_global_vector(self, vector: np.ndarray, *, global_version: int) -> None:
        assert self.trainer is not None
        fragment = make_fragment(
            trainer_type=self.trainer.get_full_state().trainer_type,
            run_id=self.run_id,
            learner_id="syncer",
            fragment_id=0,
            global_version=global_version,
            data=np.asarray(vector, dtype=np.float64),
            tokens=0,
        )
        self.trainer.apply_global_update([fragment], global_version=global_version)

    def _slow_trainer(self, factor: float) -> None:
        assert self.trainer is not None
        if hasattr(self.trainer, "slow"):
            self.trainer.slow(factor)

    def _restore_trainer_speed(self) -> None:
        assert self.trainer is not None
        if hasattr(self.trainer, "restore_speed"):
            self.trainer.restore_speed(self.baseline_throughput_tokens_per_step)

    async def _shutdown(self) -> None:
        self._write_checkpoint()
        await self._request(
            make_envelope(
                run_id=self.run_id,
                sender_id=self.learner_id,
                recipient_id="syncer",
                message_type=MessageType.LEARNER_SHUTDOWN,
                payload={"learner_id": self.learner_id},
            )
        )


async def async_main(args: argparse.Namespace) -> int:
    worker = LearnerWorker(
        learner_id=args.learner_id,
        run_id=args.run_id,
        host=args.host,
        port=args.port,
        workdir=Path(args.workdir),
        steps=args.steps,
        local_steps_per_sync=args.local_steps_per_sync,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        step_delay_seconds=args.step_delay_seconds,
        learner_lr=args.learner_lr,
        slow_factor=args.slow_factor,
        trainer_type=args.trainer_type,
        trainer_config=json.loads(args.trainer_config_json or "{}"),
        seed=args.seed,
        payload_storage_mode=args.payload_storage_mode,
        global_update_storage_mode=args.global_update_storage_mode,
        artifact_root=args.artifact_root,
        chunk_store_root=args.chunk_store_root,
        inline_payload_max_bytes=args.inline_payload_max_bytes,
        chunk_size_bytes=args.chunk_size_bytes,
        fragment_artifact_codec=args.fragment_artifact_codec,
        tensor_artifact_codec=args.tensor_artifact_codec,
        checkpoint_artifact_codec=args.checkpoint_artifact_codec,
        artifact_transfer_mode=args.artifact_transfer_mode,
    )
    return await worker.run()


def main(args: argparse.Namespace) -> int:
    return asyncio.run(async_main(args))
