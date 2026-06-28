from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.l2_remote_runtime_evidence_package import (
    build_lambda_l2_remote_runtime_evidence_package_from_dir,
)


def _write_minimal_l2_evidence(root: Path) -> None:
    (root / "syncer").mkdir(parents=True)
    (root / "learner-0").mkdir()
    (root / "learner-1").mkdir()
    (root / "layout.json").write_text(
        json.dumps(
            {
                "run_id": "lambda-l2-test",
                "roles": {
                    "syncer": {"instance_id": "syncer-i", "ip": "10.0.0.1"},
                    "learner-0": {"instance_id": "learner0-i", "ip": "10.0.0.2"},
                    "learner-1": {"instance_id": "learner1-i", "ip": "10.0.0.3"},
                },
                "syncer_port": 28080,
                "remote_instance_count": 3,
                "network_path": "remote_tcp_syncer_public_ip",
            }
        ),
        encoding="utf-8",
    )
    (root / "termination_safety.json").write_text(
        json.dumps(
            {
                "owned_instance_ids": ["syncer-i", "learner0-i", "learner1-i"],
                "observed_final_live_instance_count": 0,
                "billing_safety_status": "BILLING_SAFETY_OK",
            }
        ),
        encoding="utf-8",
    )
    commit = {
        "event_type": "sync_round_committed",
        "payload": {
            "old_global_vector": [0.0, 0.0],
            "weighted_delta": [-0.1, 0.2],
            "new_global_vector": [-0.095, 0.19],
            "previous_global_version": 0,
            "new_global_version": 1,
            "outer_lr": 0.5,
            "outer_momentum": 0.9,
            "outer_optimizer": "nesterov",
            "useful_tokens": 210,
        },
    }
    (root / "syncer" / "events.jsonl").write_text(json.dumps(commit) + "\n", encoding="utf-8")
    (root / "syncer" / "syncer_checkpoint.json").write_text(
        json.dumps(
            {
                "global_version": 1,
                "outer_optimizer_state": {
                    "outer_optimizer": "nesterov",
                    "outer_optimizer_semantics": "nesterov",
                    "step": 1,
                    "velocity": [0.1, -0.2],
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "syncer" / "syncer_summary.json").write_text(
        json.dumps(
            {
                "final_global_version": 1,
                "metrics": {
                    "committed_sync_rounds": 1,
                    "accepted_updates": 2,
                    "useful_tokens_accepted": 210,
                    "inner_optimizer_semantics": "adamw",
                    "outer_optimizer_semantics": "nesterov",
                    "nesterov_outer_optimizer_exercised": True,
                    "optimizer_state_present": True,
                    "training_attempted": True,
                    "real_training_mechanics_exercised": True,
                    "real_model_training_claimed": False,
                    "paper_scale_training_claimed": False,
                },
            }
        ),
        encoding="utf-8",
    )
    for learner_id in ("learner-0", "learner-1"):
        (root / learner_id / f"{learner_id}.checkpoint.json").write_text(
            json.dumps({"learner_id": learner_id, "trainer_type": "tiny_adamw"}),
            encoding="utf-8",
        )
        (root / learner_id / f"{learner_id}.log").write_text("{}\n", encoding="utf-8")


def test_lambda_l2_remote_runtime_evidence_package_accepts_distinct_instances(
    tmp_path: Path,
) -> None:
    _write_minimal_l2_evidence(tmp_path)

    package = build_lambda_l2_remote_runtime_evidence_package_from_dir(tmp_path)

    assert package.evidence_complete is True
    assert package.lambda_l2_remote_runtime_passed is True
    assert package.remote_instance_count == 3
    assert package.remote_process_roles == ["learner-0", "learner-1", "syncer"]
    assert package.distinct_role_instances is True
    assert package.committed_sync_rounds == 1
    assert package.inner_optimizer_semantics == "adamw"
    assert package.outer_optimizer_semantics == "nesterov"
    assert package.pseudo_gradient_numeric_check_passed is True
    assert package.independent_nesterov_max_abs_error == 0.0
    assert package.final_instance_count == 0
    assert package.launch_ready is False
    assert package.launch_allowed is False
    assert package.production_scale_ready is False
    assert package.pathway_operation_layer_ready is False
    assert package.billable_action_performed is True


def test_lambda_l2_remote_runtime_evidence_package_rejects_collocated_roles(tmp_path: Path) -> None:
    _write_minimal_l2_evidence(tmp_path)
    layout_path = tmp_path / "layout.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    layout["roles"]["learner-1"]["instance_id"] = "syncer-i"
    layout_path.write_text(json.dumps(layout), encoding="utf-8")

    package = build_lambda_l2_remote_runtime_evidence_package_from_dir(tmp_path)

    assert package.evidence_complete is False
    assert package.lambda_l2_remote_runtime_passed is False
    assert package.distinct_role_instances is False
    assert "roles_not_on_distinct_instances" in package.blockers
