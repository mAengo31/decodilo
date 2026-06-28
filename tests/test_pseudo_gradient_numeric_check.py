"""Adversarial regression: the numeric pseudo-gradient check must fail on bad math.

This guards against the field silently regressing to a tautology (the old
"Nesterov path exercised" meaning). A genuine numeric verifier must:
  - pass on a correctly logged Nesterov commit sequence,
  - fail when a logged new_global_vector is tampered with,
  - fail (not pass) when there are no committed rounds.

Pure in-process / no sockets. No Lambda, no remote, no spend.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from decodilo.runtime.local_runner import LocalRunConfig, LocalRunner
from decodilo.syncer.event_log import EventLog, EventType
from decodilo.syncer.outer_optimizer import create_outer_optimizer


def _build_runner(workdir: Path) -> LocalRunner:
    config = LocalRunConfig(
        learners=2,
        steps=1,
        min_quorum=2,
        seed=1,
        workdir=workdir,
        report_json=workdir / "report.json",
        vector_dim=3,
        fragments=1,
        outer_optimizer="nesterov",
        trainer_type="tiny_adamw",
        trainer_config={"optimizer": "adamw"},
    )
    return LocalRunner(config)


def _write_good_nesterov_log(workdir: Path) -> Path:
    log = EventLog(workdir / "events.jsonl", run_id="pg-num", truncate=True)
    optimizer = create_outer_optimizer("nesterov", outer_lr=0.5, momentum=0.9)
    global_vector = np.array([1.0, -2.0, 0.5], dtype=np.float64)
    deltas = [
        np.array([0.01, -0.02, 0.03], dtype=np.float64),
        np.array([0.02, -0.01, 0.01], dtype=np.float64),
    ]
    for index, delta in enumerate(deltas):
        old = global_vector.copy()
        global_vector = optimizer.apply(old, delta)
        log.append(
            EventType.SYNC_ROUND_COMMITTED,
            logical_time=index,
            payload={
                "round_id": f"r{index}",
                "previous_global_version": index,
                "new_global_version": index + 1,
                "accepted_learner_ids": ["l0", "l1"],
                "token_weights": {"l0": 0.5, "l1": 0.5},
                "useful_tokens": 42,
                "outer_optimizer": "nesterov",
                "outer_lr": 0.5,
                "outer_momentum": 0.9,
                "old_global_vector": old.tolist(),
                "weighted_delta": delta.tolist(),
                "new_global_vector": global_vector.tolist(),
            },
        )
    return workdir / "events.jsonl"


def test_numeric_check_passes_on_correct_log(tmp_path) -> None:
    runner = _build_runner(tmp_path)
    log_path = _write_good_nesterov_log(tmp_path)
    result = runner._verify_pseudo_gradient_numeric(log_path)
    assert result["passed"] is True
    assert result["rounds_checked"] == 2
    assert result["reason"] is None


def test_numeric_check_fails_on_tampered_new_global_vector(tmp_path) -> None:
    runner = _build_runner(tmp_path)
    log_path = _write_good_nesterov_log(tmp_path)
    records = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for record in records:
        if record.get("event_type") == "sync_round_committed":
            record["payload"]["new_global_vector"][0] += 0.5  # corrupt the math
    tampered = tmp_path / "events_tampered.jsonl"
    tampered.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    result = runner._verify_pseudo_gradient_numeric(tampered)
    assert result["passed"] is False
    assert result["reason"] == "recomputed_new_global_vector_mismatch"


def test_numeric_check_fails_on_empty_log(tmp_path) -> None:
    runner = _build_runner(tmp_path)
    empty = tmp_path / "events_empty.jsonl"
    empty.write_text("", encoding="utf-8")
    result = runner._verify_pseudo_gradient_numeric(empty)
    assert result["passed"] is False
    assert result["reason"] == "no_committed_rounds"
