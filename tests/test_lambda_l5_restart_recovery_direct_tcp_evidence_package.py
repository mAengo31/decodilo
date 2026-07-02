from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.l5_restart_recovery_direct_tcp_evidence_package import (
    build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir,
)


def _write_minimal_l5_evidence(
    root: Path,
    *,
    learners: int = 2,
    experiment_mode: str = "restart_recovery",
) -> None:
    (root / "syncer").mkdir(parents=True)
    for index in range(learners):
        (root / f"learner-{index}").mkdir()
    (root / "layout.json").write_text(
        json.dumps(
            {
                "run_id": "lambda-l5-test",
                "roles": {
                    "syncer": {"instance_id": "syncer-i", "ip": "10.0.0.1"},
                    **{
                        f"learner-{index}": {
                            "instance_id": f"learner{index}-i",
                            "ip": f"10.0.0.{index + 2}",
                        }
                        for index in range(learners)
                    },
                },
                "syncer_port": 28080,
                "remote_instance_count": learners + 1,
                "network_path": "lambda_firewall_direct_tcp",
                "experiment_mode": experiment_mode,
            }
        ),
        encoding="utf-8",
    )
    (root / "firewall_audit.json").write_text(
        json.dumps({"restored": True, "temporary_rule_count": 2}),
        encoding="utf-8",
    )
    (root / "network_probe.json").write_text(
        json.dumps({"direct_tcp_probe_passed": True}),
        encoding="utf-8",
    )
    (root / "restart_audit.json").write_text(
        json.dumps(
            {
                "attempted": True,
                "recovered": True,
                "restart_round": 1,
                "rounds_after_restart": 1,
                "experiment_mode": experiment_mode,
            }
        ),
        encoding="utf-8",
    )
    (root / "termination_safety.json").write_text(
        json.dumps(
            {
                "owned_instance_ids": [
                    "syncer-i",
                    *[f"learner{index}-i" for index in range(learners)],
                ],
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
            "accepted_learner_ids": ["learner-0"],
        },
    }
    commit2 = {
        "event_type": "sync_round_committed",
        "payload": {
            "old_global_vector": [-0.095, 0.19],
            "weighted_delta": [0.05, -0.1],
            "new_global_vector": [-0.088, 0.176],
            "previous_global_version": 1,
            "new_global_version": 2,
            "outer_lr": 0.5,
            "outer_momentum": 0.9,
            "outer_optimizer": "nesterov",
            "useful_tokens": 210,
            "accepted_learner_ids": ["learner-1"],
        },
    }
    (root / "syncer" / "events.jsonl").write_text(
        json.dumps(commit) + "\n" + json.dumps(commit2) + "\n",
        encoding="utf-8",
    )
    (root / "syncer" / "syncer_checkpoint.json").write_text(
        json.dumps(
            {
                "global_version": 2,
                "outer_optimizer_state": {
                    "outer_optimizer": "nesterov",
                    "outer_optimizer_semantics": "nesterov",
                    "step": 2,
                    "velocity": [0.04, -0.08],
                },
            }
        ),
        encoding="utf-8",
    )
    (root / "syncer" / "syncer_summary.json").write_text(
        json.dumps(
            {
                "final_global_version": 2,
                "metrics": {
                    "committed_sync_rounds": 2,
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
    for learner_id in [f"learner-{index}" for index in range(learners)]:
        (root / learner_id / f"{learner_id}.checkpoint.json").write_text(
            json.dumps({"learner_id": learner_id, "trainer_type": "tiny_adamw"}),
            encoding="utf-8",
        )
        (root / learner_id / f"{learner_id}.log").write_text("{}\n", encoding="utf-8")


def test_lambda_l5_restart_recovery_direct_tcp_evidence_package_accepts_distinct_instances(
    tmp_path: Path,
) -> None:
    _write_minimal_l5_evidence(tmp_path)

    package = build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir(tmp_path)

    assert package.evidence_complete is True
    assert package.lambda_l5_restart_recovery_direct_tcp_passed is True
    assert package.remote_instance_count == 3
    assert package.remote_process_roles == ["learner-0", "learner-1", "syncer"]
    assert package.distinct_role_instances is True
    assert package.network_path == "lambda_firewall_direct_tcp"
    assert package.firewall_rules_restored is True
    assert package.direct_tcp_probe_passed is True
    assert package.restart_attempted is True
    assert package.restart_recovered is True
    assert package.restart_round == 1
    assert package.rounds_after_restart == 1
    assert package.committed_sync_rounds == 2
    assert package.inner_optimizer_semantics == "adamw"
    assert package.outer_optimizer_semantics == "nesterov"
    assert package.pseudo_gradient_numeric_check_passed is True
    assert package.independent_nesterov_max_abs_error is not None
    assert package.independent_nesterov_max_abs_error < 1e-12
    assert package.final_instance_count == 0
    assert package.launch_ready is False
    assert package.launch_allowed is False
    assert package.production_scale_ready is False
    assert package.pathway_operation_layer_ready is False
    assert package.billable_action_performed is True




def test_lambda_l5_evidence_package_accepts_four_learner_roles(tmp_path: Path) -> None:
    _write_minimal_l5_evidence(tmp_path, learners=4)

    package = build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir(tmp_path)

    assert package.evidence_complete is True
    assert package.lambda_l5_restart_recovery_direct_tcp_passed is True
    assert package.remote_instance_count == 5
    assert package.remote_process_roles == [
        "learner-0",
        "learner-1",
        "learner-2",
        "learner-3",
        "syncer",
    ]
    assert package.learner_artifacts_present == [
        "learner-0",
        "learner-1",
        "learner-2",
        "learner-3",
    ]


def test_lambda_l5_evidence_package_accepts_scale_only_no_restart(
    tmp_path: Path,
) -> None:
    _write_minimal_l5_evidence(tmp_path, learners=4, experiment_mode="scale_only_no_restart")
    (tmp_path / "restart_audit.json").write_text(
        json.dumps(
            {
                "attempted": False,
                "recovered": False,
                "skipped": True,
                "skip_reason": "scale_only_no_restart",
                "experiment_mode": "scale_only_no_restart",
                "restart_round": None,
                "rounds_after_restart": 0,
            }
        ),
        encoding="utf-8",
    )

    package = build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir(tmp_path)

    assert package.evidence_complete is True
    assert package.experiment_mode == "scale_only_no_restart"
    assert package.lambda_l5_restart_recovery_direct_tcp_passed is False
    assert package.lambda_l5_scale_only_direct_tcp_passed is True
    assert package.restart_attempted is False
    assert package.restart_recovered is False
    assert package.committed_sync_rounds == 2
    assert package.pseudo_gradient_numeric_check_passed is True
    assert package.blockers == []


def test_lambda_l5_scale_only_evidence_can_derive_empty_summary(
    tmp_path: Path,
) -> None:
    _write_minimal_l5_evidence(tmp_path, learners=4, experiment_mode="scale_only_no_restart")
    (tmp_path / "restart_audit.json").write_text(
        json.dumps(
            {
                "attempted": False,
                "recovered": False,
                "skipped": True,
                "skip_reason": "scale_only_no_restart",
                "experiment_mode": "scale_only_no_restart",
                "restart_round": None,
                "rounds_after_restart": 0,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "syncer" / "syncer_summary.json").write_text("", encoding="utf-8")

    package = build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir(tmp_path)

    assert package.evidence_complete is True
    assert package.lambda_l5_scale_only_direct_tcp_passed is True
    assert package.committed_sync_rounds == 2
    assert package.accepted_updates == 2
    assert package.useful_tokens_accepted == 420
    assert package.inner_optimizer_semantics == "adamw"
    assert package.outer_optimizer_semantics == "nesterov"

def test_lambda_l5_restart_recovery_direct_tcp_evidence_package_rejects_collocated_roles(
    tmp_path: Path,
) -> None:
    _write_minimal_l5_evidence(tmp_path)
    layout_path = tmp_path / "layout.json"
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    layout["roles"]["learner-1"]["instance_id"] = "syncer-i"
    layout_path.write_text(json.dumps(layout), encoding="utf-8")

    package = build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir(tmp_path)

    assert package.evidence_complete is False
    assert package.lambda_l5_restart_recovery_direct_tcp_passed is False
    assert package.distinct_role_instances is False
    assert "roles_not_on_distinct_instances" in package.blockers


def test_lambda_l5_restart_recovery_direct_tcp_evidence_package_rejects_no_rounds_after_restart(
    tmp_path: Path,
) -> None:
    _write_minimal_l5_evidence(tmp_path)
    (tmp_path / "restart_audit.json").write_text(
        json.dumps(
            {
                "attempted": True,
                "recovered": True,
                "restart_round": 2,
                "rounds_after_restart": 0,
            }
        ),
        encoding="utf-8",
    )

    package = build_lambda_l5_restart_recovery_direct_tcp_evidence_package_from_dir(tmp_path)

    assert package.evidence_complete is False
    assert "no_rounds_after_restart" in package.blockers
