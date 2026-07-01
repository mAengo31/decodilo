from __future__ import annotations

import json

from decodilo.operation import LambdaOperationBackend, run_operation
from decodilo.operation.lambda_components import LambdaOperationBackendConfig


def test_pathway_lite_compiles_next_lambda_gpu_chunked_managed_experiment(tmp_path) -> None:
    from decodilo.operation.pathway import (
        build_next_lambda_gpu_chunked_experiment,
        compile_pathway_managed_experiment,
    )

    spec = build_next_lambda_gpu_chunked_experiment(
        name="lambda-gpu-chunked-next",
        steps=16,
        restart_syncer_after_round=2,
    )
    plan = compile_pathway_managed_experiment(
        spec,
        workdir=tmp_path,
        lambda_config=LambdaOperationBackendConfig(
            run_id="lambda-gpu-chunked-next-dry-run",
            evidence_root=tmp_path / "evidence",
            ssh_key_name="test-key",
            ssh_private_key=tmp_path / "private-key.pem",
            restart_after_round=2,
        ),
    )

    assert plan.pathway_layer == "pathway_lite"
    assert plan.next_managed_experiment == "lambda_gpu_torch_causal_lm_chunked_transport"
    assert plan.operation_spec.trainer_type == "torch_causal_lm"
    assert plan.operation_spec.trainer_config["device"] == "cuda"
    assert plan.operation_spec.inner_optimizer == "adamw"
    assert plan.operation_spec.outer_optimizer == "nesterov"
    assert plan.operation_spec.payload_storage_mode == "chunked"
    assert plan.operation_spec.checkpoint_storage_mode == "chunked"
    assert plan.operation_spec.merge_mode == "streaming_chunked"
    assert plan.operation_spec.global_update_storage_mode == "chunked"

    assert plan.lambda_plan.remote_roles == ["syncer", "learner-0", "learner-1"]
    assert plan.lambda_plan.launch_ready is False
    assert plan.lambda_plan.launch_allowed is False
    assert "actual_device_cuda" in plan.required_evidence
    assert "global_update_artifact_ref_present" in plan.required_evidence
    assert "metadata_only_event_log" in plan.required_evidence
    assert "firewall_rules_restored" in plan.required_evidence
    assert "final_instance_count_zero" in plan.required_evidence

    command = plan.lambda_plan.command
    assert command[command.index("--trainer-type") + 1] == "torch_causal_lm"
    assert command[command.index("--payload-storage-mode") + 1] == "chunked"
    assert command[command.index("--checkpoint-storage-mode") + 1] == "chunked"
    assert command[command.index("--merge-mode") + 1] == "streaming_chunked"
    assert command[command.index("--global-update-storage-mode") + 1] == "chunked"

    rendered = json.loads(plan.to_json())
    assert rendered["launch_ready"] is False
    assert rendered["launch_allowed"] is False
    assert rendered["billable_action_performed"] is False
    assert rendered["lambda_plan"]["global_update_storage_mode"] == "chunked"


def test_pathway_chunked_lambda_backend_is_fail_closed_but_preserves_plan(tmp_path) -> None:
    from decodilo.operation.pathway import build_next_lambda_gpu_chunked_experiment

    spec = build_next_lambda_gpu_chunked_experiment(
        name="blocked-pathway-chunked-lambda",
        steps=16,
        restart_syncer_after_round=2,
    )
    result = run_operation(
        spec,
        workdir=tmp_path,
        backend=LambdaOperationBackend(
            config=LambdaOperationBackendConfig(
                allow_billable_action=False,
                run_id="blocked-pathway-chunked-lambda",
                evidence_root=tmp_path / "evidence",
                ssh_key_name="test-key",
                ssh_private_key=tmp_path / "private-key.pem",
                restart_after_round=2,
            )
        ),
    )

    assert result.backend == "lambda"
    assert result.status == "blocked"
    assert result.safety.launch_ready is False
    assert result.safety.launch_allowed is False
    assert result.safety.billable_action_performed is False
    plan = result.backend_report["operation_plan"]
    assert plan["trainer_type"] == "torch_causal_lm"
    assert plan["payload_storage_mode"] == "chunked"
    assert plan["checkpoint_storage_mode"] == "chunked"
    assert plan["merge_mode"] == "streaming_chunked"
    assert plan["global_update_storage_mode"] == "chunked"
    assert plan["launch_ready"] is False
    assert plan["launch_allowed"] is False
    command = result.backend_report["command"]
    assert "--payload-storage-mode" in command
    assert command[command.index("--payload-storage-mode") + 1] == "chunked"
    assert command[command.index("--global-update-storage-mode") + 1] == "chunked"


def test_pathway_compiles_six_step_production_candidate_profiles(tmp_path) -> None:
    from decodilo.operation.pathway import compile_six_step_production_candidate

    plans = compile_six_step_production_candidate(
        workdir=tmp_path,
        lambda_config=LambdaOperationBackendConfig(
            run_id="six-step-dry-run",
            evidence_root=tmp_path / "evidence",
            ssh_key_name="test-key",
            ssh_private_key=tmp_path / "private-key.pem",
            restart_after_round=2,
        ),
    )

    assert set(plans) == {"larger_model", "more_learners", "failure_matrix"}
    larger = plans["larger_model"]
    assert larger.pathway_layer == "pathway_lite_six_step_candidate"
    assert larger.operation_spec.vector_dim == 29_424
    assert larger.operation_spec.artifact_transfer_mode == "object_store"
    assert larger.operation_spec.production_step_tags == [
        "larger_model",
        "artifact_pressure",
        "object_store",
    ]
    assert larger.lambda_plan.command[
        larger.lambda_plan.command.index("--artifact-transfer-mode") + 1
    ] == "object_store"
    assert larger.lambda_plan.launch_ready is False
    assert larger.lambda_plan.launch_allowed is False
    assert "larger_model_above_13k_parameters" in larger.required_evidence
    assert "external_durable_backend_not_claimed" in larger.required_evidence

    more = plans["more_learners"]
    assert more.operation_spec.learners == 4
    assert more.operation_spec.min_quorum == 3
    assert more.operation_spec.artifact_transfer_mode == "object_store"
    assert more.lambda_plan.remote_roles == [
        "syncer",
        "learner-0",
        "learner-1",
        "learner-2",
        "learner-3",
    ]

    failure = plans["failure_matrix"]
    assert "failure_matrix" in failure.operation_spec.production_step_tags
    assert failure.operation_spec.restart_syncer_after_round == 2
