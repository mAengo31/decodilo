"""Supervisor for local syncer plus learner subprocesses."""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from decodilo import __version__
from decodilo.pricing.budget import (
    BudgetGuard,
    RunBudgetManifest,
    build_run_budget_manifest,
    hourly_cost_for_cluster,
)
from decodilo.pricing.freshness import require_usable_snapshot
from decodilo.pricing.registry import load_price_snapshot, query_snapshot_price
from decodilo.runtime.artifact_manifest import build_artifact_manifest, write_artifact_manifest
from decodilo.runtime.chaos_plan import (
    RoundAction,
    SlowLearnerAction,
    parse_round_action,
    parse_slow_action,
)
from decodilo.runtime.chunked_payloads import default_artifact_root, default_chunk_store_root
from decodilo.runtime.chunked_runtime_modes import validate_runtime_modes
from decodilo.runtime.metrics_validation import validate_metrics, validate_report_payload
from decodilo.runtime.perf_counters import PerfTimer, nonnegative_perf_counters
from decodilo.runtime.reports import (
    LocalRuntimeReport,
    ProcessSummary,
    ReplayValidationReport,
)
from decodilo.runtime.resource_limits import RuntimeResourceLimits
from decodilo.runtime.run_spec import (
    RunSpec,
    load_run_spec,
    make_run_spec_from_config,
    write_run_spec,
)
from decodilo.sim.fake_model import convex_loss, make_target_vector
from decodilo.sim.runner import SimulationConfig, deterministic_run_id
from decodilo.storage.codec_registry import validate_artifact_codec
from decodilo.syncer.event_log import EventType, read_event_log
from decodilo.syncer.outer_optimizer import create_outer_optimizer
from decodilo.syncer.replay import replay_event_log
from decodilo.time_compat import UTC
from decodilo.transport.envelope import MessageType, make_envelope
from decodilo.transport.tcp_client import JsonlTcpClient


@dataclass(frozen=True)
class LocalRunConfig:
    learners: int
    steps: int
    min_quorum: int
    seed: int
    workdir: Path
    report_json: Path
    vector_dim: int = 8
    fragments: int = 2
    local_steps_per_sync: int = 10
    grace_window: int = 0
    max_staleness: int = 1
    learner_lr: float = 0.05
    outer_optimizer: str = "sgd"
    outer_lr: float = 1.0
    outer_momentum: float = 0.9
    trainer_type: str = "numpy_convex"
    trainer_config: dict[str, Any] | None = None
    heartbeat_interval_seconds: float = 0.05
    heartbeat_timeout_seconds: float = 0.2
    update_long_poll_timeout_seconds: float = 0.005
    step_delay_seconds: float = 0.005
    max_pending_messages_per_learner: int = 128
    max_pending_fragments_per_learner: int = 1
    max_inflight_bytes_per_learner: int = 2_000_000
    max_total_inflight_bytes: int = 10_000_000
    syncer_checkpoint_interval_rounds: int = 0
    restart_syncer_after_round: int | None = None
    syncer_restart_timeout_seconds: float = 3.0
    price_snapshot: Path | None = None
    allow_sample_prices: bool = False
    allow_stale_prices: bool = False
    credits: float | None = None
    gpu_type: str | None = None
    gpus_per_instance: int | None = None
    instances: int = 1
    hours: float | None = None
    max_run_budget: float | None = None
    safety_buffer_pct: float = 0.15
    run_id: str | None = None
    kill_learner: RoundAction | None = None
    restart_learner: RoundAction | None = None
    slow_learner: SlowLearnerAction | None = None
    restore_learner: RoundAction | None = None
    memory_budget_mb: int | None = None
    allow_spill_to_disk: bool = False
    spill_dir: Path | None = None
    max_spill_mb: int | None = None
    chunked_checkpoints: bool = False
    payload_storage_mode: str = "inline"
    checkpoint_storage_mode: str = "inline"
    merge_mode: str = "in_memory"
    global_update_storage_mode: str = "inline"
    chunk_store_root: Path | None = None
    artifact_root: Path | None = None
    inline_payload_max_bytes: int = 1_000_000
    chunk_size_bytes: int = 1024 * 1024
    require_chunked_for_large_state: bool = False
    tensor_artifact_codec: str = "json_safe"
    fragment_artifact_codec: str = "json_safe"
    checkpoint_artifact_codec: str = "json_safe"
    artifact_transfer_mode: str = "bundle"
    artifact_storage_backend: str = "auto"


class LocalRunner:
    """Owns local child processes and report assembly."""

    def __init__(self, config: LocalRunConfig) -> None:
        self.config = config
        sim_config = SimulationConfig(
            learners=config.learners,
            vector_dim=config.vector_dim,
            num_fragments=config.fragments,
            steps=config.steps,
            local_steps_per_sync=config.local_steps_per_sync,
            min_quorum=config.min_quorum,
            grace_window_ticks=config.grace_window,
            max_staleness_versions=config.max_staleness,
            seed=config.seed,
            learner_lr=config.learner_lr,
            outer_lr=config.outer_lr,
            run_id=config.run_id,
        )
        self.run_id = config.run_id or deterministic_run_id(sim_config)
        self.syncer_proc: subprocess.Popen[str] | None = None
        self.learners: dict[str, list[subprocess.Popen[str]]] = {}
        self.killed_learners: list[str] = []
        self.restarted_learners: list[str] = []
        self.slowed_learners: list[str] = []
        self.restored_learners: list[str] = []
        self.orphan_cleanup_performed = False
        self.ready_file = config.workdir / "syncer_ready.json"
        self.control_sequences: dict[str, int] = {}
        self.budget_manifest: RunBudgetManifest | None = None
        self.syncer_restarts: list[int] = []
        self.run_spec: RunSpec | None = None
        self.run_spec_path = config.workdir / "run_spec.json"
        self.artifact_manifest_path = config.workdir / "artifacts.json"
        self.budget_manifest_path = config.workdir / "budget_manifest.json"
        self.perf_timer = PerfTimer()
        validate_runtime_modes(
            payload_storage_mode=config.payload_storage_mode,
            checkpoint_storage_mode=config.checkpoint_storage_mode,
            merge_mode=config.merge_mode,
            global_update_storage_mode=config.global_update_storage_mode,
        )
        validate_artifact_codec(config.tensor_artifact_codec)
        validate_artifact_codec(config.fragment_artifact_codec)
        validate_artifact_codec(config.checkpoint_artifact_codec)

    def run(self) -> LocalRuntimeReport:
        started_at = datetime.now(UTC).isoformat()
        self.config.workdir.mkdir(parents=True, exist_ok=True)
        self.budget_manifest = self._build_budget_manifest_if_configured()
        if self.budget_manifest is not None:
            self.budget_manifest_path.write_text(
                json.dumps(self.budget_manifest.model_dump(mode="json"), indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
        self.run_spec = make_run_spec_from_config(
            self.config,
            run_id=self.run_id,
            pricing_manifest=(
                self.budget_manifest.model_dump(mode="json") if self.budget_manifest else None
            ),
        )
        write_run_spec(self.run_spec_path, self.run_spec)
        try:
            ready = self._start_syncer(recover=False)
            self._start_all_learners(ready)
            self._monitor_learners()
            ready = json.loads(self.ready_file.read_text(encoding="utf-8"))
            syncer_summary = asyncio.run(self._shutdown_syncer(ready))
            report = self._build_report(syncer_summary, started_at=started_at)
            self._write_report(report)
            if self.config.chunked_checkpoints:
                self._write_chunked_checkpoint_artifacts()
            self._write_artifact_manifest()
            return report
        finally:
            self._cleanup_children()

    def _start_syncer(self, *, recover: bool) -> dict[str, Any]:
        self.ready_file.unlink(missing_ok=True)
        command = [
            sys.executable,
            "-m",
            "decodilo.cli",
            "syncer",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            "0",
            "--ready-file",
            str(self.ready_file),
            "--workdir",
            str(self.config.workdir),
            "--run-id",
            self.run_id,
            "--learners",
            str(self.config.learners),
            "--steps",
            str(self.config.steps),
            "--vector-dim",
            str(self.config.vector_dim),
            "--fragments",
            str(self.config.fragments),
            "--local-steps-per-sync",
            str(self.config.local_steps_per_sync),
            "--min-quorum",
            str(self.config.min_quorum),
            "--grace-window",
            str(self.config.grace_window),
            "--max-staleness",
            str(self.config.max_staleness),
            "--seed",
            str(self.config.seed),
            "--learner-lr",
            str(self.config.learner_lr),
            "--outer-lr",
            str(self.config.outer_lr),
            "--outer-optimizer",
            self.config.outer_optimizer,
            "--outer-momentum",
            str(self.config.outer_momentum),
            "--heartbeat-timeout-seconds",
            str(self.config.heartbeat_timeout_seconds),
            "--update-long-poll-timeout-seconds",
            str(self.config.update_long_poll_timeout_seconds),
            "--max-pending-messages-per-learner",
            str(self.config.max_pending_messages_per_learner),
            "--max-pending-fragments-per-learner",
            str(self.config.max_pending_fragments_per_learner),
            "--max-inflight-bytes-per-learner",
            str(self.config.max_inflight_bytes_per_learner),
            "--max-total-inflight-bytes",
            str(self.config.max_total_inflight_bytes),
            "--syncer-checkpoint-interval-rounds",
            str(self.config.syncer_checkpoint_interval_rounds),
            "--syncer-checkpoint-path",
            str(self.config.workdir / "syncer_checkpoint.json"),
            "--payload-storage-mode",
            self.config.payload_storage_mode,
            "--checkpoint-storage-mode",
            self.config.checkpoint_storage_mode,
            "--merge-mode",
            self.config.merge_mode,
            "--global-update-storage-mode",
            self.config.global_update_storage_mode,
            "--artifact-root",
            str(self.config.artifact_root or default_artifact_root(self.config.workdir)),
            "--chunk-store-root",
            str(self.config.chunk_store_root or default_chunk_store_root(self.config.workdir)),
            "--inline-payload-max-bytes",
            str(self.config.inline_payload_max_bytes),
            "--chunk-size-bytes",
            str(self.config.chunk_size_bytes),
            "--tensor-artifact-codec",
            self.config.tensor_artifact_codec,
            "--fragment-artifact-codec",
            self.config.fragment_artifact_codec,
            "--checkpoint-artifact-codec",
            self.config.checkpoint_artifact_codec,
            "--artifact-transfer-mode",
            self.config.artifact_transfer_mode,
            "--artifact-storage-backend",
            self.config.artifact_storage_backend,
        ]
        if recover:
            command.append("--recover-from-checkpoint")
        self.syncer_proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            if self.syncer_proc.poll() is not None:
                stdout, stderr = self.syncer_proc.communicate(timeout=1)
                raise RuntimeError(f"syncer exited early\nstdout={stdout}\nstderr={stderr}")
            if self.ready_file.exists():
                return json.loads(self.ready_file.read_text(encoding="utf-8"))
            time.sleep(0.02)
        raise TimeoutError("syncer did not write ready file")

    def _start_all_learners(self, ready: dict[str, Any]) -> None:
        for index in range(self.config.learners):
            learner_id = f"learner-{index}"
            self._start_learner(learner_id, ready)

    def _start_learner(self, learner_id: str, ready: dict[str, Any]) -> None:
        command = [
            sys.executable,
            "-m",
            "decodilo.cli",
            "learner",
            "run",
            "--learner-id",
            learner_id,
            "--run-id",
            self.run_id,
            "--host",
            str(ready["host"]),
            "--port",
            str(ready["port"]),
            "--workdir",
            str(self.config.workdir),
            "--steps",
            str(self.config.steps),
            "--local-steps-per-sync",
            str(self.config.local_steps_per_sync),
            "--heartbeat-interval-seconds",
            str(self.config.heartbeat_interval_seconds),
            "--step-delay-seconds",
            str(self.config.step_delay_seconds),
            "--learner-lr",
            str(self.config.learner_lr),
            "--trainer-type",
            self.config.trainer_type,
            "--trainer-config-json",
            json.dumps(self.config.trainer_config or {}, sort_keys=True),
            "--seed",
            str(self.config.seed),
            "--payload-storage-mode",
            self.config.payload_storage_mode,
            "--global-update-storage-mode",
            self.config.global_update_storage_mode,
            "--artifact-root",
            str(self.config.artifact_root or default_artifact_root(self.config.workdir)),
            "--chunk-store-root",
            str(self.config.chunk_store_root or default_chunk_store_root(self.config.workdir)),
            "--inline-payload-max-bytes",
            str(self.config.inline_payload_max_bytes),
            "--chunk-size-bytes",
            str(self.config.chunk_size_bytes),
            "--fragment-artifact-codec",
            self.config.fragment_artifact_codec,
            "--tensor-artifact-codec",
            self.config.tensor_artifact_codec,
            "--checkpoint-artifact-codec",
            self.config.checkpoint_artifact_codec,
            "--artifact-transfer-mode",
            self.config.artifact_transfer_mode,
            "--artifact-storage-backend",
            self.config.artifact_storage_backend,
        ]
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.learners.setdefault(learner_id, []).append(proc)

    def _monitor_learners(self) -> None:
        run_timeout = max(8.0, self.config.steps * self.config.step_delay_seconds + 5)
        deadline = time.monotonic() + run_timeout
        killed = False
        restarted = False
        slowed = False
        restored = False
        syncer_restarted = False
        while time.monotonic() < deadline:
            committed = self._committed_rounds()
            if (
                self.config.restart_syncer_after_round is not None
                and not syncer_restarted
                and committed >= self.config.restart_syncer_after_round
            ):
                self._restart_syncer()
                syncer_restarted = True
            if self.config.kill_learner and not killed:
                if committed >= self.config.kill_learner.after_round:
                    self._kill_learner(self.config.kill_learner.learner_id)
                    killed = True
            if self.config.restart_learner and killed and not restarted:
                if committed >= self.config.restart_learner.after_round:
                    ready = json.loads(self.ready_file.read_text(encoding="utf-8"))
                    self._start_learner(self.config.restart_learner.learner_id, ready)
                    self.restarted_learners.append(self.config.restart_learner.learner_id)
                    restarted = True
            if self.config.slow_learner and not slowed:
                if committed >= self.config.slow_learner.after_round:
                    self._write_control(
                        self.config.slow_learner.learner_id,
                        {"slow_factor": self.config.slow_learner.factor},
                    )
                    self.slowed_learners.append(self.config.slow_learner.learner_id)
                    slowed = True
            if self.config.restore_learner and not restored:
                if committed >= self.config.restore_learner.after_round:
                    self._write_control(
                        self.config.restore_learner.learner_id,
                        {"restore": True},
                    )
                    self.restored_learners.append(self.config.restore_learner.learner_id)
                    restored = True

            live = [
                proc
                for procs in self.learners.values()
                for proc in procs
                if proc.poll() is None
            ]
            if not live:
                break
            time.sleep(0.02)
        time.sleep(self.config.heartbeat_timeout_seconds + 0.05)

    def _restart_syncer(self) -> None:
        if self.syncer_proc is not None and self.syncer_proc.poll() is None:
            clean_stop = False
            if self.ready_file.exists():
                try:
                    ready = json.loads(self.ready_file.read_text(encoding="utf-8"))
                    asyncio.run(self._shutdown_syncer(ready))
                    self.syncer_proc.wait(timeout=self.config.syncer_restart_timeout_seconds)
                    clean_stop = True
                except Exception:
                    clean_stop = False
            if not clean_stop:
                self.syncer_proc.terminate()
                try:
                    self.syncer_proc.wait(timeout=self.config.syncer_restart_timeout_seconds)
                except subprocess.TimeoutExpired:
                    self.syncer_proc.kill()
                    self.orphan_cleanup_performed = True
        self._start_syncer(recover=True)
        self.syncer_restarts.append(self._committed_rounds())

    def _write_control(self, learner_id: str, payload: dict[str, Any]) -> None:
        sequence = self.control_sequences.get(learner_id, 0) + 1
        self.control_sequences[learner_id] = sequence
        control = {"sequence": sequence, **payload}
        (self.config.workdir / f"{learner_id}.control.json").write_text(
            json.dumps(control, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _kill_learner(self, learner_id: str) -> None:
        procs = self.learners.get(learner_id, [])
        if not procs:
            return
        proc = procs[-1]
        if proc.poll() is None:
            proc.kill()
            self.killed_learners.append(learner_id)

    def _committed_rounds(self) -> int:
        path = self.config.workdir / "events.jsonl"
        if not path.exists():
            return 0
        count = 0
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if '"event_type":"sync_round_committed"' in line:
                    count += 1
        return count

    async def _shutdown_syncer(self, ready: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        response = None
        shutdown_timeout = min(
            2.0,
            max(0.5, self.config.heartbeat_timeout_seconds + 0.5),
        )
        for _ in range(3):
            try:
                async with JsonlTcpClient(
                    host=str(ready["host"]),
                    port=int(ready["port"]),
                    timeout_seconds=shutdown_timeout,
                ) as client:
                    response = await client.request(
                        make_envelope(
                            run_id=self.run_id,
                            sender_id="supervisor",
                            recipient_id="syncer",
                            message_type=MessageType.SYNCER_SHUTDOWN,
                            payload={"reason": "local_runner_complete"},
                        )
                    )
                break
            except Exception as exc:  # noqa: BLE001 - retry local shutdown transport
                last_error = exc
                await asyncio.sleep(0.1)
        if response is None:
            if self.syncer_proc is not None and self.syncer_proc.poll() is None:
                self.syncer_proc.terminate()
                self.orphan_cleanup_performed = True
                try:
                    self.syncer_proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.syncer_proc.kill()
            return self._fallback_summary_from_replay(
                reason=f"syncer shutdown timed out; synthesized summary from replay: {last_error}"
            )
        if response.message_type == MessageType.ERROR:
            raise RuntimeError(f"syncer shutdown failed: {response.payload}")
        if self.syncer_proc is not None:
            try:
                self.syncer_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.syncer_proc.terminate()
                self.orphan_cleanup_performed = True
        return response.payload

    def _fallback_summary_from_replay(self, *, reason: str) -> dict[str, Any]:
        event_log_path = self.config.workdir / "events.jsonl"
        replay = replay_event_log(event_log_path)
        vector = (
            replay.final_global_vector
            if replay.final_global_vector is not None
            else make_target_vector(self.config.vector_dim, seed=self.config.seed) * 0.0
        )
        target = make_target_vector(len(vector), seed=self.config.seed)
        useful = replay.accepted_useful_tokens
        total = max(useful, 0)
        return {
            "run_id": self.run_id,
            "final_global_version": replay.global_versions[-1] if replay.global_versions else 0,
            "final_global_vector": vector.astype(float).tolist(),
            "final_loss": convex_loss(vector, target),
            "trainer_state_kind": "unknown",
            "trainer_metrics": {
                "trainer_state_bytes_estimate": None,
                "trainer_num_parameters": None,
                "trainer_final_loss": None,
                "trainer_final_eval_loss": None,
                "trainer_nonfinite_detected": False,
            },
            "metrics": {
                "total_tokens_processed": total,
                "useful_tokens_accepted": useful,
                "rejected_tokens": replay.rejected_tokens,
                "stale_tokens": replay.stale_tokens,
                "wasted_tokens": max(total - useful, 0),
                "committed_sync_rounds": replay.sync_rounds_committed,
                "sync_rounds_committed": replay.sync_rounds_committed,
                "skipped_sync_rounds": replay.skipped_sync_rounds,
                "rejected_fragments": replay.rejected_update_count,
                "stale_fragments": 0,
                "goodput_ratio": useful / total if total else 0.0,
                "accepted_updates": replay.sync_rounds_committed,
                "global_update_messages_sent": 0,
                "global_update_acks": 0,
            },
            "unhealthy_learners": [],
            "recovery_source": "event_log_fallback",
            "event_log_path": str(event_log_path),
            "code_version": __version__ or None,
            "warnings": [reason],
        }

    def _verify_pseudo_gradient_numeric(self, event_log_path: Path) -> dict[str, Any]:
        """Numerically re-derive logged outer optimizer steps from inline commit events.

        The syncer can cheaply report that the Nesterov path was exercised, but
        that is not a mathematical pseudo-gradient check. This verifier is run
        while building the final local report and independently reapplies the
        declared outer optimizer to each committed round's logged
        old_global_vector + weighted_delta. It then compares the recomputed
        vector to the logged new_global_vector.

        Returns passed=None when the event payloads are not inline-vector
        payloads (for example artifact-ref/chunked modes).
        """
        optimizer = None
        optimizer_name: str | None = None
        rounds_checked = 0
        try:
            events = read_event_log(event_log_path)
            for event in events:
                if event.event_type != EventType.SYNC_ROUND_COMMITTED:
                    continue
                payload = event.payload
                required = {"old_global_vector", "weighted_delta", "new_global_vector"}
                if not required.issubset(payload):
                    return {
                        "passed": None,
                        "rounds_checked": rounds_checked,
                        "reason": "inline_vectors_unavailable",
                    }
                name = str(payload.get("outer_optimizer", "sgd"))
                if optimizer is None or optimizer_name != name:
                    outer_momentum = payload.get("outer_momentum", 0.9)
                    optimizer = create_outer_optimizer(
                        name,
                        outer_lr=float(payload["outer_lr"]),
                        momentum=0.9 if outer_momentum is None else float(outer_momentum),
                    )
                    optimizer_name = name
                old_vector = np.asarray(payload["old_global_vector"], dtype=np.float64)
                weighted_delta = np.asarray(payload["weighted_delta"], dtype=np.float64)
                logged_new = np.asarray(payload["new_global_vector"], dtype=np.float64)
                recomputed = optimizer.apply(old_vector, weighted_delta)
                if not np.allclose(recomputed, logged_new, rtol=0.0, atol=1e-12):
                    return {
                        "passed": False,
                        "rounds_checked": rounds_checked + 1,
                        "reason": "recomputed_new_global_vector_mismatch",
                    }
                rounds_checked += 1
        except Exception as exc:  # noqa: BLE001 - report verifier failure verbatim
            return {"passed": False, "rounds_checked": rounds_checked, "reason": str(exc)}
        if rounds_checked == 0:
            return {"passed": False, "rounds_checked": 0, "reason": "no_committed_rounds"}
        return {"passed": True, "rounds_checked": rounds_checked, "reason": None}

    def _build_report(
        self,
        syncer_summary: dict[str, Any],
        *,
        started_at: str,
    ) -> LocalRuntimeReport:
        event_log_path = self.config.workdir / "events.jsonl"
        try:
            replay = replay_event_log(event_log_path)
            replay_report = ReplayValidationReport(
                replay_passed=True,
                replay_final_global_version=(
                    replay.global_versions[-1] if replay.global_versions else 0
                ),
                replay_useful_tokens_accepted=replay.accepted_useful_tokens,
            )
        except Exception as exc:  # noqa: BLE001 - report validation failure verbatim
            replay_report = ReplayValidationReport(
                replay_passed=False,
                replay_error=str(exc),
            )
        learner_pids = {
            learner_id: [proc.pid for proc in procs] for learner_id, procs in self.learners.items()
        }
        exit_codes = {
            f"{learner_id}#{index}": proc.poll()
            for learner_id, procs in self.learners.items()
            for index, proc in enumerate(procs)
        }
        process_summary = ProcessSummary(
            syncer_pid=self.syncer_proc.pid if self.syncer_proc is not None else -1,
            learner_pids=learner_pids,
            exit_codes=exit_codes,
            killed_learners=self.killed_learners,
            restarted_learners=self.restarted_learners,
            slowed_learners=self.slowed_learners,
            restored_learners=self.restored_learners,
            syncer_restarts=self.syncer_restarts,
            unhealthy_learners_observed=syncer_summary.get("unhealthy_learners", []),
            orphan_cleanup_performed=self.orphan_cleanup_performed,
        )
        config_dict = asdict(self.config)
        config_dict["workdir"] = str(self.config.workdir)
        config_dict["report_json"] = str(self.config.report_json)
        if self.config.price_snapshot is not None:
            config_dict["price_snapshot"] = str(self.config.price_snapshot)
        if self.config.kill_learner is not None:
            config_dict["kill_learner"] = asdict(self.config.kill_learner)
        if self.config.restart_learner is not None:
            config_dict["restart_learner"] = asdict(self.config.restart_learner)
        if self.config.slow_learner is not None:
            config_dict["slow_learner"] = asdict(self.config.slow_learner)
        if self.config.restore_learner is not None:
            config_dict["restore_learner"] = asdict(self.config.restore_learner)
        if self.config.spill_dir is not None:
            config_dict["spill_dir"] = str(self.config.spill_dir)
        if self.config.chunk_store_root is not None:
            config_dict["chunk_store_root"] = str(self.config.chunk_store_root)
        if self.config.artifact_root is not None:
            config_dict["artifact_root"] = str(self.config.artifact_root)
        resource_limits = RuntimeResourceLimits.from_mb(
            memory_budget_mb=self.config.memory_budget_mb,
            spill_dir=self.config.spill_dir,
            allow_spill_to_disk=self.config.allow_spill_to_disk,
            max_spill_mb=self.config.max_spill_mb,
            chunked_checkpoints=self.config.chunked_checkpoints,
        )
        bytes_serialized = sum(
            path.stat().st_size
            for path in self.config.workdir.glob("**/*")
            if path.is_file()
        )
        perf_counters = nonnegative_perf_counters(
            wall_time_seconds=self.perf_timer.elapsed(),
            bytes_serialized=bytes_serialized,
            bytes_deserialized=bytes_serialized,
            transport_messages_sent=int(
                syncer_summary.get("metrics", {}).get("transport_messages_sent", 0)
            ),
            transport_messages_received=int(
                syncer_summary.get("metrics", {}).get("transport_messages_received", 0)
            ),
            transport_bytes_sent=int(
                syncer_summary.get("metrics", {}).get("transport_bytes_sent", 0)
            ),
            transport_bytes_received=int(
                syncer_summary.get("metrics", {}).get("transport_bytes_received", 0)
            ),
            peak_in_memory_bytes_estimate=max(
                int(syncer_summary.get("metrics", {}).get("inflight_bytes_peak", 0)),
                resource_limits.max_in_memory_fragment_bytes,
            ),
        )
        metrics_payload = dict(syncer_summary["metrics"])
        numeric_pseudo = self._verify_pseudo_gradient_numeric(event_log_path)
        metrics_payload["pseudo_gradient_numeric_check_passed"] = numeric_pseudo["passed"]
        metrics_payload["pseudo_gradient_numeric_rounds_checked"] = numeric_pseudo[
            "rounds_checked"
        ]
        metrics_payload["pseudo_gradient_numeric_check_reason"] = numeric_pseudo["reason"]
        # Backward-compatible alias, now backed by numeric event-log re-derivation
        # whenever the local runtime can read inline vectors from commit events.
        metrics_payload["pseudo_gradient_check_passed"] = numeric_pseudo["passed"]

        report = LocalRuntimeReport(
            run_id=self.run_id,
            config=config_dict,
            process_summary=process_summary,
            final_global_version=int(syncer_summary["final_global_version"]),
            final_loss=float(syncer_summary["final_loss"]),
            recovery_source=syncer_summary.get("recovery_source"),
            trainer_type=self.config.trainer_type,
            trainer_state_kind=str(syncer_summary.get("trainer_state_kind", "flat")),
            trainer_config=self.config.trainer_config or {},
            trainer_state_bytes_estimate=syncer_summary.get("trainer_metrics", {}).get(
                "trainer_state_bytes_estimate"
            ),
            trainer_num_parameters=syncer_summary.get("trainer_metrics", {}).get(
                "trainer_num_parameters"
            ),
            trainer_final_loss=syncer_summary.get("trainer_metrics", {}).get(
                "trainer_final_loss"
            ),
            trainer_final_eval_loss=syncer_summary.get("trainer_metrics", {}).get(
                "trainer_final_eval_loss"
            ),
            trainer_nonfinite_detected=bool(
                syncer_summary.get("trainer_metrics", {}).get("trainer_nonfinite_detected", False)
            ),
            trainer_checkpoint_paths=[
                str(path) for path in sorted(self.config.workdir.glob("learner-*.checkpoint.json"))
            ],
            perf_counters=perf_counters.model_dump(mode="json"),
            metrics=metrics_payload,
            metric_validation=validate_metrics(
                metrics_payload,
                final_global_version=int(syncer_summary["final_global_version"]),
            ).model_dump(mode="json"),
            replay_validation=replay_report,
            budget_manifest=(
                self.budget_manifest.model_dump(mode="json") if self.budget_manifest else None
            ),
            run_spec_path=str(self.run_spec_path),
            run_spec_sha256=self.run_spec.sha256() if self.run_spec is not None else None,
            artifact_manifest_path=str(self.artifact_manifest_path),
            event_log_path=str(event_log_path),
            learner_logs={
                learner_id: str(self.config.workdir / f"{learner_id}.log")
                for learner_id in self.learners
            },
            started_at_utc=started_at,
            finished_at_utc=datetime.now(UTC).isoformat(),
            code_version=__version__ or None,
            artifact_transfer_mode=str(
                syncer_summary.get("artifact_transfer_mode", self.config.artifact_transfer_mode)
            ),
            artifact_storage_backend=str(
                syncer_summary.get("artifact_storage_backend", "local_filesystem")
            ),
        )
        return report.model_copy(
            update={
                "metric_validation": validate_report_payload(
                    report.model_dump(mode="json")
                ).model_dump(mode="json")
            }
        )

    def _write_artifact_manifest(self) -> None:
        learner_checkpoint_paths = sorted(self.config.workdir.glob("learner-*.checkpoint.json"))
        learner_log_paths = sorted(self.config.workdir.glob("learner-*.log"))
        syncer_checkpoint_paths = sorted(self.config.workdir.glob("syncer_checkpoint.json"))
        price_snapshot_paths = [self.config.price_snapshot] if self.config.price_snapshot else []
        chunked_checkpoint_paths = sorted(
            (self.config.workdir / "chunked_checkpoints").glob("*.artifact.json")
        )
        live_checkpoint_paths = sorted(
            (self.config.workdir / "live_checkpoints").glob("*.artifact.json")
        )
        live_artifact_paths = sorted(
            (self.config.artifact_root or default_artifact_root(self.config.workdir)).glob(
                "**/*.json"
            )
        )
        lifecycle_artifact_paths = [
            *sorted((self.config.workdir / "recovery_manifests").glob("*.json")),
            *sorted((self.config.workdir / "event_segments").glob("*.jsonl")),
            *sorted((self.config.workdir / "event_segments").glob("*.json")),
            *sorted(self.config.workdir.glob("replay_snapshot*.json")),
            *sorted(self.config.workdir.glob("compact_report*.json")),
            *sorted(self.config.workdir.glob("gc_plan*.json")),
            *sorted(self.config.workdir.glob("artifact_audit*.json")),
            *sorted(self.config.workdir.glob("preflight*.json")),
        ]
        spill_artifact_paths = sorted(
            self.config.spill_dir.glob("manifests/*.json")
            if self.config.spill_dir is not None and self.config.spill_dir.exists()
            else []
        )
        manifest = build_artifact_manifest(
            run_id=self.run_id,
            workdir=self.config.workdir,
            run_spec_path=self.run_spec_path,
            report_path=self.config.report_json,
            event_log_path=self.config.workdir / "events.jsonl",
            syncer_checkpoint_paths=syncer_checkpoint_paths,
            learner_checkpoint_paths=[
                *learner_checkpoint_paths,
                *chunked_checkpoint_paths,
                *live_checkpoint_paths,
                *live_artifact_paths,
            ],
            learner_log_paths=learner_log_paths,
            price_snapshot_paths=price_snapshot_paths,
            spill_artifact_paths=spill_artifact_paths,
            budget_manifest_path=(
                self.budget_manifest_path if self.budget_manifest is not None else None
            ),
            recovery_manifest_path=(
                self.config.workdir / "recovery_manifest.json"
                if (self.config.workdir / "recovery_manifest.json").exists()
                else None
            ),
            lifecycle_artifact_paths=lifecycle_artifact_paths,
        )
        write_artifact_manifest(self.artifact_manifest_path, manifest)

    def _write_chunked_checkpoint_artifacts(self) -> None:
        from decodilo.runtime.learner_checkpoint import (
            load_checkpoint,
            write_chunked_learner_checkpoint,
        )
        from decodilo.runtime.syncer_checkpoint import (
            load_syncer_checkpoint,
            write_chunked_syncer_checkpoint,
        )

        manifest_dir = self.config.workdir / "chunked_checkpoints"
        chunk_dir = manifest_dir / "store"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(self.config.workdir.glob("learner-*.checkpoint.json")):
            checkpoint = load_checkpoint(path)
            write_chunked_learner_checkpoint(
                manifest_path=manifest_dir / f"{path.stem}.artifact.json",
                chunk_store_dir=chunk_dir,
                checkpoint=checkpoint,
                chunk_size_bytes=64 * 1024,
            )
        syncer_path = self.config.workdir / "syncer_checkpoint.json"
        if syncer_path.exists():
            checkpoint = load_syncer_checkpoint(syncer_path)
            write_chunked_syncer_checkpoint(
                manifest_path=manifest_dir / "syncer_checkpoint.artifact.json",
                chunk_store_dir=chunk_dir,
                checkpoint=checkpoint,
                chunk_size_bytes=64 * 1024,
            )

    def _build_budget_manifest_if_configured(self) -> RunBudgetManifest | None:
        supplied = [
            self.config.price_snapshot,
            self.config.credits,
            self.config.gpu_type,
            self.config.gpus_per_instance,
            self.config.hours,
        ]
        if all(value is None for value in supplied):
            return None
        if any(value is None for value in supplied):
            raise ValueError(
                "local pricing requires --price-snapshot, --credits, --gpu-type, "
                "--gpus-per-instance, and --hours"
            )
        assert self.config.price_snapshot is not None
        assert self.config.credits is not None
        assert self.config.gpu_type is not None
        assert self.config.gpus_per_instance is not None
        assert self.config.hours is not None

        snapshot = load_price_snapshot(self.config.price_snapshot)
        require_usable_snapshot(
            snapshot,
            allow_sample_prices=self.config.allow_sample_prices,
            allow_stale_prices=self.config.allow_stale_prices,
        )
        record = query_snapshot_price(
            snapshot,
            gpu_type=self.config.gpu_type,
            gpus_per_instance=self.config.gpus_per_instance,
        )
        price = record.to_price_profile()
        estimated_cost = hourly_cost_for_cluster(self.config.instances, price) * self.config.hours
        max_budget = (
            self.config.max_run_budget
            if self.config.max_run_budget is not None
            else self.config.credits
        )
        guard = BudgetGuard(
            starting_credits=self.config.credits,
            safety_buffer_pct=self.config.safety_buffer_pct,
        )
        decision = guard.require_run_allowed(
            estimated_run_cost=estimated_cost,
            max_run_budget=max_budget,
        )
        return build_run_budget_manifest(
            run_id=self.run_id,
            provider=snapshot.provider,
            mode="local",
            price_snapshot_id=snapshot.snapshot_id,
            selected_price_record_ids=[record.record_id],
            planned_instances=self.config.instances,
            gpus_per_instance=record.gpus_per_instance,
            planned_hours=self.config.hours,
            base_estimated_cost=estimated_cost,
            safety_buffer_percentage=self.config.safety_buffer_pct,
            safety_buffer_adjusted_cost=decision.safety_buffer_adjusted_cost,
            max_run_budget=max_budget,
            starting_credits=self.config.credits,
            projected_remaining_credits=decision.projected_remaining_credits,
            allow_sample_prices=self.config.allow_sample_prices,
            allow_stale_prices=self.config.allow_stale_prices,
            notes="local CPU runtime; no cloud resources are launched",
        )

    def _write_report(self, report: LocalRuntimeReport) -> None:
        self.config.report_json.parent.mkdir(parents=True, exist_ok=True)
        self.config.report_json.write_text(
            json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _cleanup_children(self) -> None:
        for procs in self.learners.values():
            for proc in procs:
                if proc.poll() is None:
                    proc.terminate()
                    self.orphan_cleanup_performed = True
                    try:
                        proc.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        proc.kill()
        if self.syncer_proc is not None and self.syncer_proc.poll() is None:
            self.syncer_proc.terminate()
            self.orphan_cleanup_performed = True
            try:
                self.syncer_proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.syncer_proc.kill()


def _trainer_config_from_args(args: argparse.Namespace) -> dict[str, Any]:
    raw = getattr(args, "trainer_config_json", None)
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("--trainer-config-json must decode to a JSON object")
    return parsed


def _effective_trainer_type(args: argparse.Namespace) -> str:
    return str(getattr(args, "trainer", None) or getattr(args, "trainer_type", "numpy_convex"))


def _effective_vector_dim(
    *,
    trainer_type: str,
    trainer_config: dict[str, Any],
    requested_vector_dim: int,
) -> int:
    if trainer_type != "torch_causal_lm":
        return requested_vector_dim
    from decodilo.trainer.torch_causal_lm import estimate_causal_lm_num_parameters

    return estimate_causal_lm_num_parameters(
        vocab_size=int(trainer_config.get("vocab_size", 64)),
        seq_len=int(trainer_config.get("seq_len", 16)),
        d_model=int(trainer_config.get("d_model", 32)),
        num_layers=int(trainer_config.get("num_layers", 1)),
        mlp_ratio=float(trainer_config.get("mlp_ratio", 2.0)),
    )


def build_config_from_args(args: argparse.Namespace) -> LocalRunConfig:
    if getattr(args, "run_spec", None) is not None:
        spec = load_run_spec(args.run_spec)
        workdir = Path(args.workdir) if args.workdir is not None else Path(args.run_spec).parent
        report_json = (
            Path(args.report_json)
            if args.report_json is not None
            else workdir / "report.json"
        )
        heartbeat = spec.heartbeat_settings
        update = spec.update_delivery_settings
        backpressure = spec.backpressure_settings
        checkpoint = spec.checkpoint_settings
        trainer_config = {
            key: value
            for key, value in spec.trainer_config.items()
            if key not in {"learner_lr", "outer_lr"}
        }
        return LocalRunConfig(
            learners=spec.learners,
            steps=spec.steps,
            min_quorum=spec.min_quorum,
            seed=spec.seed,
            workdir=workdir,
            report_json=report_json,
            vector_dim=spec.vector_dim,
            fragments=spec.num_fragments,
            local_steps_per_sync=spec.local_steps_per_sync,
            grace_window=spec.grace_window,
            max_staleness=spec.max_staleness_versions,
            learner_lr=float(spec.trainer_config.get("learner_lr", args.learner_lr)),
            outer_optimizer=str(spec.trainer_config.get("outer_optimizer", args.outer_optimizer)),
            outer_lr=float(spec.trainer_config.get("outer_lr", args.outer_lr)),
            outer_momentum=float(
                spec.trainer_config.get("outer_momentum", args.outer_momentum)
            ),
            trainer_type=spec.trainer_type,
            trainer_config=trainer_config,
            heartbeat_interval_seconds=float(
                heartbeat.get("heartbeat_interval_seconds", args.heartbeat_interval_seconds)
            ),
            heartbeat_timeout_seconds=float(
                heartbeat.get("heartbeat_timeout_seconds", args.heartbeat_timeout_seconds)
            ),
            update_long_poll_timeout_seconds=float(
                update.get(
                    "update_long_poll_timeout_seconds",
                    args.update_long_poll_timeout_seconds,
                )
            ),
            step_delay_seconds=args.step_delay_seconds,
            max_pending_messages_per_learner=int(
                backpressure.get(
                    "max_pending_messages_per_learner",
                    args.max_pending_messages_per_learner,
                )
            ),
            max_pending_fragments_per_learner=int(
                backpressure.get(
                    "max_pending_fragments_per_learner",
                    args.max_pending_fragments_per_learner,
                )
            ),
            max_inflight_bytes_per_learner=int(
                backpressure.get(
                    "max_inflight_bytes_per_learner",
                    args.max_inflight_bytes_per_learner,
                )
            ),
            max_total_inflight_bytes=int(
                backpressure.get("max_total_inflight_bytes", args.max_total_inflight_bytes)
            ),
            memory_budget_mb=backpressure.get("memory_budget_mb"),
            allow_spill_to_disk=bool(backpressure.get("allow_spill_to_disk", False)),
            spill_dir=(
                Path(backpressure["spill_dir"]) if backpressure.get("spill_dir") else None
            ),
            max_spill_mb=backpressure.get("max_spill_mb"),
            syncer_checkpoint_interval_rounds=int(
                checkpoint.get(
                    "syncer_checkpoint_interval_rounds",
                    args.syncer_checkpoint_interval_rounds
                    or (1 if spec.chaos_plan.get("restart_syncer_after_round") else 0),
                )
            ),
            restart_syncer_after_round=spec.chaos_plan.get("restart_syncer_after_round"),
            chunked_checkpoints=bool(checkpoint.get("chunked_checkpoints", False)),
            payload_storage_mode=spec.payload_storage_mode,
            checkpoint_storage_mode=spec.checkpoint_storage_mode,
            merge_mode=spec.merge_mode,
            global_update_storage_mode=spec.global_update_storage_mode,
            chunk_store_root=Path(spec.chunk_store_root) if spec.chunk_store_root else None,
            artifact_root=Path(spec.artifact_root) if spec.artifact_root else None,
            inline_payload_max_bytes=spec.inline_payload_max_bytes,
            chunk_size_bytes=spec.chunk_size_bytes,
            require_chunked_for_large_state=spec.require_chunked_for_large_state,
            tensor_artifact_codec=spec.tensor_artifact_codec,
            fragment_artifact_codec=spec.fragment_artifact_codec,
            checkpoint_artifact_codec=spec.checkpoint_artifact_codec,
            run_id=spec.run_id,
        )
    if args.workdir is None or args.report_json is None:
        raise ValueError("--workdir and --report-json are required unless --run-spec is supplied")
    trainer_type = _effective_trainer_type(args)
    trainer_config = _trainer_config_from_args(args)
    vector_dim = _effective_vector_dim(
        trainer_type=trainer_type,
        trainer_config=trainer_config,
        requested_vector_dim=args.vector_dim,
    )
    return LocalRunConfig(
        learners=args.learners,
        steps=args.steps,
        min_quorum=args.min_quorum,
        seed=args.seed,
        workdir=Path(args.workdir),
        report_json=Path(args.report_json),
        vector_dim=vector_dim,
        fragments=args.fragments,
        local_steps_per_sync=args.local_steps_per_sync,
        grace_window=args.grace_window,
        max_staleness=args.max_staleness,
        learner_lr=args.learner_lr,
        outer_optimizer=args.outer_optimizer,
        outer_lr=args.outer_lr,
        outer_momentum=args.outer_momentum,
        trainer_type=trainer_type,
        trainer_config=trainer_config,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        heartbeat_timeout_seconds=args.heartbeat_timeout_seconds,
        update_long_poll_timeout_seconds=args.update_long_poll_timeout_seconds,
        step_delay_seconds=args.step_delay_seconds,
        max_pending_messages_per_learner=args.max_pending_messages_per_learner,
        max_pending_fragments_per_learner=args.max_pending_fragments_per_learner,
        max_inflight_bytes_per_learner=args.max_inflight_bytes_per_learner,
        max_total_inflight_bytes=args.max_total_inflight_bytes,
        syncer_checkpoint_interval_rounds=(
            args.syncer_checkpoint_interval_rounds
            or (1 if args.restart_syncer_after_round is not None else 0)
        ),
        restart_syncer_after_round=args.restart_syncer_after_round,
        syncer_restart_timeout_seconds=args.syncer_restart_timeout_seconds,
        price_snapshot=args.price_snapshot,
        allow_sample_prices=args.allow_sample_prices,
        allow_stale_prices=args.allow_stale_prices,
        credits=args.credits,
        gpu_type=args.gpu_type,
        gpus_per_instance=args.gpus_per_instance,
        instances=args.instances,
        hours=args.hours,
        max_run_budget=args.max_run_budget,
        safety_buffer_pct=args.safety_buffer_pct,
        run_id=args.run_id,
        kill_learner=parse_round_action(args.kill_learner),
        restart_learner=parse_round_action(args.restart_learner),
        slow_learner=parse_slow_action(args.slow_learner),
        restore_learner=parse_round_action(args.restore_learner),
        memory_budget_mb=args.memory_budget_mb,
        allow_spill_to_disk=args.allow_spill_to_disk,
        spill_dir=args.spill_dir,
        max_spill_mb=args.max_spill_mb,
        chunked_checkpoints=args.chunked_checkpoints
        or args.checkpoint_storage_mode in {"chunked", "dual"},
        payload_storage_mode=args.payload_storage_mode,
        checkpoint_storage_mode=(
            "dual" if args.chunked_checkpoints else args.checkpoint_storage_mode
        ),
        merge_mode=args.merge_mode,
        global_update_storage_mode=args.global_update_storage_mode,
        chunk_store_root=args.chunk_store_root,
        artifact_root=args.artifact_root,
        inline_payload_max_bytes=args.inline_payload_max_bytes,
        chunk_size_bytes=args.chunk_size_mb * 1024 * 1024,
        require_chunked_for_large_state=args.require_chunked_for_large_state,
        tensor_artifact_codec=args.tensor_artifact_codec,
        fragment_artifact_codec=args.fragment_artifact_codec,
        checkpoint_artifact_codec=args.checkpoint_artifact_codec,
        artifact_transfer_mode=args.artifact_transfer_mode,
        artifact_storage_backend=args.artifact_storage_backend,
    )


def main(args: argparse.Namespace) -> int:
    runner = LocalRunner(build_config_from_args(args))
    report = runner.run()
    summary = {
        "run_id": report.run_id,
        "committed_sync_rounds": report.metrics.get("committed_sync_rounds"),
        "useful_tokens_accepted": report.metrics.get("useful_tokens_accepted"),
        "replay_passed": report.replay_validation.replay_passed,
        "metric_validation_passed": report.metric_validation.get("passed"),
        "report_json": str(report.config.get("report_json")),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    passed = report.replay_validation.replay_passed and report.metric_validation.get("passed")
    return 0 if passed else 1
