"""Phase 1 hardening: restart/checkpoint recovery for the AdamW/Nesterov local path.

These tests harden the exact local DiLoCo optimizer experiment by proving the
Nesterov outer-optimizer state (momentum velocity + step) survives a syncer
checkpoint/restart, and that the live local learner/syncer runtime recovers a
mid-run syncer restart while still passing replay validation.

Boundary: local-only, CPU-only, synthetic. No Lambda, no remote backend, no
network beyond localhost, no spend.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys

import numpy as np
import pytest

from decodilo.runtime.syncer_service import SyncerService, SyncerServiceConfig
from decodilo.transport.envelope import MessageType, make_envelope

pytestmark = [pytest.mark.integration, pytest.mark.runtime]


def _submit(service, *, learner_id, vector, version_seen, key):
    envelope = make_envelope(
        run_id=service.config.run_id,
        sender_id=learner_id,
        recipient_id="syncer",
        message_type=MessageType.SUBMIT_FRAGMENT,
        idempotency_key=key,
        payload={
            "vector": list(vector),
            "global_version_seen": version_seen,
            "tokens": 21,
            "tokens_processed": 21 * (version_seen + 1),
            "inner_optimizer": "adamw",
            "inner_optimizer_semantics": "adamw",
            "training_attempted": True,
            "real_training_mechanics_exercised": True,
            "real_model_training_claimed": False,
            "paper_scale_training_claimed": False,
            "optimizer_state": {"step": version_seen + 1},
        },
    )
    return asyncio.run(service.handle_envelope(envelope))


def _commit_one_round(service, round_index):
    """Drive a single quorum commit from two learners; return new global_version."""
    version_seen = service.store.global_version
    base = service.store.global_vector
    _submit(
        service,
        learner_id="learner-0",
        vector=base + 0.01 * (round_index + 1),
        version_seen=version_seen,
        key=f"k-{round_index}-l0",
    )
    _submit(
        service,
        learner_id="learner-1",
        vector=base - 0.02 * (round_index + 1),
        version_seen=version_seen,
        key=f"k-{round_index}-l1",
    )
    return service.store.global_version


def _make_config(tmp_path, *, recover):
    return SyncerServiceConfig(
        run_id="run-nesterov-recovery",
        workdir=tmp_path,
        learners=2,
        vector_dim=3,
        num_fragments=1,
        min_quorum=2,
        max_staleness_versions=1,
        outer_optimizer="nesterov",
        outer_lr=0.5,
        outer_momentum=0.9,
        syncer_checkpoint_interval_rounds=1,
        recover_from_checkpoint=recover,
    )


def test_nesterov_outer_state_survives_syncer_checkpoint_restart(tmp_path) -> None:
    service = SyncerService(_make_config(tmp_path, recover=False))

    v1 = _commit_one_round(service, 0)
    v2 = _commit_one_round(service, 1)
    assert v1 == 1
    assert v2 == 2
    assert service.store.metrics.sync_rounds_committed == 2

    pre_step = int(service.store.optimizer.step)
    pre_velocity = np.asarray(service.store.optimizer.velocity, dtype=np.float64).copy()
    pre_global_version = service.store.global_version
    pre_global_vector = service.store.global_vector.copy()
    assert pre_step == 2
    assert np.any(pre_velocity != 0.0)

    service._write_syncer_checkpoint()

    recovered = SyncerService(_make_config(tmp_path, recover=True))

    from decodilo.syncer.outer_optimizer import NesterovOuterOptimizer

    assert isinstance(recovered.store.optimizer, NesterovOuterOptimizer)
    assert int(recovered.store.optimizer.step) == pre_step
    np.testing.assert_allclose(
        np.asarray(recovered.store.optimizer.velocity, dtype=np.float64),
        pre_velocity,
        rtol=0.0,
        atol=1e-12,
    )
    assert recovered.store.global_version == pre_global_version
    np.testing.assert_allclose(
        recovered.store.global_vector, pre_global_vector, rtol=0.0, atol=1e-12
    )

    _commit_one_round(recovered, 2)
    assert int(recovered.store.optimizer.step) == pre_step + 1
    assert recovered.store.global_version == pre_global_version + 1
    assert not np.allclose(
        np.asarray(recovered.store.optimizer.velocity, dtype=np.float64),
        pre_velocity,
        rtol=0.0,
        atol=1e-12,
    )


def test_live_local_runtime_recovers_syncer_restart_with_adamw_nesterov(tmp_path) -> None:
    report_path = tmp_path / "report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "local",
            "run",
            "--trainer",
            "tiny_adamw",
            "--trainer-config-json",
            json.dumps({"optimizer": "adamw"}, sort_keys=True),
            "--outer-optimizer",
            "nesterov",
            "--outer-lr",
            "0.5",
            "--learners",
            "2",
            "--steps",
            "30",
            "--min-quorum",
            "2",
            "--seed",
            "123",
            "--workdir",
            str(tmp_path),
            "--report-json",
            str(report_path),
            "--local-steps-per-sync",
            "1",
            "--fragments",
            "1",
            "--heartbeat-timeout-seconds",
            "2",
            "--syncer-checkpoint-interval-rounds",
            "1",
            "--restart-syncer-after-round",
            "2",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    events_text = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    checkpoint = json.loads((tmp_path / "syncer_checkpoint.json").read_text(encoding="utf-8"))

    assert completed.returncode == 0
    assert report["process_summary"]["syncer_restarts"]
    assert "syncer_recovered" in events_text

    assert report["metrics"]["outer_optimizer_semantics"] == "nesterov"
    assert report["metrics"]["inner_optimizer_semantics"] == "adamw"
    assert checkpoint["outer_optimizer_state"]["outer_optimizer"] == "nesterov"
    assert checkpoint["outer_optimizer_state"]["step"] == report["final_global_version"]
    assert any(abs(v) > 0.0 for v in checkpoint["outer_optimizer_state"]["velocity"])

    assert report["final_global_version"] >= 2
    assert report["replay_validation"]["replay_passed"] is True
    assert report["metric_validation"]["passed"] is True
    assert report["metrics"]["nesterov_outer_optimizer_exercised"] is True
    assert report["metrics"]["pseudo_gradient_numeric_check_passed"] is True
    assert report["metrics"]["pseudo_gradient_numeric_rounds_checked"] >= 1

    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert report["billable_action_performed"] is False
    assert report["remote_backend_enabled"] is False
    assert report["network_scope"] == "localhost_only"
