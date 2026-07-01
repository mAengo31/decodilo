from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_runner():
    path = Path(__file__).resolve().parents[1] / "tools" / "lambda_l5_runner.py"
    spec = importlib.util.spec_from_file_location("lambda_l5_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["lambda_l5_runner"] = module
    spec.loader.exec_module(module)
    return module


def test_temporary_firewall_rules_preserve_existing_rules_and_scope_l5_port() -> None:
    runner = _load_runner()
    original = [
        {
            "protocol": "tcp",
            "port_range": [22, 22],
            "source_network": "0.0.0.0/0",
            "description": "Allow SSH connections from any IP",
        },
        {
            "protocol": "icmp",
            "source_network": "0.0.0.0/0",
            "description": "Allow Ping from any IP",
        },
    ]

    rules = runner._temporary_firewall_rules(
        original,
        port=28080,
        learner_ips=["203.0.113.10", "203.0.113.11"],
    )

    assert original[0] in rules
    assert original[1] in rules
    l5_rules = [rule for rule in rules if rule.get("port_range") == [28080, 28080]]
    assert l5_rules == [
        {
            "protocol": "tcp",
            "port_range": [28080, 28080],
            "source_network": "203.0.113.10/32",
            "description": "Temporary Decodilo L5 learner-0 direct TCP syncer access",
        },
        {
            "protocol": "tcp",
            "port_range": [28080, 28080],
            "source_network": "203.0.113.11/32",
            "description": "Temporary Decodilo L5 learner-1 direct TCP syncer access",
        },
    ]


def test_restart_recovery_sufficient_requires_post_restart_round() -> None:
    runner = _load_runner()

    assert runner._restart_recovery_sufficient(
        restart_round=24,
        recovered=True,
        final_round=59,
    ) is True
    assert runner._restart_recovery_sufficient(
        restart_round=24,
        recovered=True,
        final_round=24,
    ) is False
    assert runner._restart_recovery_sufficient(
        restart_round=None,
        recovered=True,
        final_round=59,
    ) is False
    assert runner._restart_recovery_sufficient(
        restart_round=24,
        recovered=False,
        final_round=59,
    ) is False


def test_l5_runner_commands_accept_torch_causal_lm_args(tmp_path: Path) -> None:
    runner = _load_runner()
    args = type(
        "Args",
        (),
        {
            "port": 28080,
            "run_id": "lambda-l5-gpu",
            "trainer_type": "torch_causal_lm",
            "trainer_config_json": '{"device":"cuda","optimizer":"adamw"}',
            "vector_dim": 1234,
            "learners": 2,
            "steps": 8,
            "min_quorum": 2,
            "local_steps_per_sync": 1,
            "fragments": 1,
        },
    )()


    syncer_command = runner._syncer_command(args)
    learner_command = runner._learner_command(args, "learner-0", "127.0.0.1")

    assert "--vector-dim 1234" in syncer_command
    assert "--steps 8" in syncer_command
    assert "--trainer-type torch_causal_lm" in learner_command
    assert "--trainer-config-json" in learner_command
    assert "device" in learner_command
    assert "cuda" in learner_command
    assert "--steps 8" in learner_command


def test_l5_runner_commands_accept_chunked_transport_args(tmp_path: Path) -> None:
    runner = _load_runner()
    args = type(
        "Args",
        (),
        {
            "port": 28080,
            "run_id": "lambda-l5-gpu-chunked",
            "trainer_type": "torch_causal_lm",
            "trainer_config_json": '{"device":"cuda","optimizer":"adamw"}',
            "vector_dim": 3408,
            "learners": 4,
            "steps": 16,
            "min_quorum": 2,
            "local_steps_per_sync": 1,
            "fragments": 1,
            "payload_storage_mode": "chunked",
            "checkpoint_storage_mode": "chunked",
            "merge_mode": "streaming_chunked",
            "global_update_storage_mode": "chunked",
            "chunk_size_mb": 1,
            "inline_payload_max_bytes": 1024,
            "artifact_transfer_mode": "object_store",
        },
    )()


    assert runner._learner_roles(args) == ["learner-0", "learner-1", "learner-2", "learner-3"]
    assert runner._all_roles(args) == [
        "syncer",
        "learner-0",
        "learner-1",
        "learner-2",
        "learner-3",
    ]

    syncer_command = runner._syncer_command(args)
    learner_command = runner._learner_command(args, "learner-0", "127.0.0.1")

    for command in [syncer_command, learner_command]:
        assert "--payload-storage-mode chunked" in command
        assert "--global-update-storage-mode chunked" in command
        assert "--chunk-size" in command or "--chunk-size-bytes" in command
        assert "--artifact-transfer-mode object_store" in command
    assert "--checkpoint-storage-mode chunked" in syncer_command
    assert "--merge-mode streaming_chunked" in syncer_command
