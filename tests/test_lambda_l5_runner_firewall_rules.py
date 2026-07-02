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
            "artifact_storage_backend": "durable_filesystem_object_store",
            "learner_reconnect_timeout_seconds": 90.0,
            "learner_run_timeout_seconds": 300.0,
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
        assert "--artifact-storage-backend durable_filesystem_object_store" in command
    assert "--checkpoint-storage-mode chunked" in syncer_command
    assert "--merge-mode streaming_chunked" in syncer_command


def test_l5_api_retries_429_rate_limit_with_retry_after(monkeypatch) -> None:
    import io
    from urllib.error import HTTPError

    runner = _load_runner()
    calls = {"count": 0}
    sleeps: list[float] = []

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"data": {}}'

    def fake_urlopen(_req, timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            raise HTTPError(
                url="https://" + "cloud.lambdalabs.com/api/v1/instances",
                code=429,
                msg="Too Many Requests",
                hdrs={"Retry-After": "30"},
                fp=io.BytesIO(b'{"retry_after": 30}'),
            )
        return _Response()

    monkeypatch.setattr(runner, "urlopen", fake_urlopen)
    monkeypatch.setattr(runner.time, "sleep", sleeps.append)

    assert runner._api("api-key", "GET", "/instances") == {"data": {}}
    assert calls["count"] == 2
    assert sleeps == [30.0]


def test_l5_launch_owned_instances_can_be_paced(monkeypatch) -> None:
    runner = _load_runner()
    sleeps: list[float] = []
    launched: list[tuple[str, str, str]] = []
    args = type(
        "Args",
        (),
        {
            "learners": 2,
            "region": "us-east-1",
            "instance_type": "gpu_1x_a10",
            "launch_delay_seconds": 45.0,
        },
    )()

    def fake_launch(_api_key, region, instance_type, _ssh_key_name):
        launched.append((region, instance_type, f"id-{len(launched)}"))
        return launched[-1][2]

    monkeypatch.setattr(runner, "_launch_instance", fake_launch)
    monkeypatch.setattr(runner.time, "sleep", sleeps.append)

    owned = runner._launch_owned_instances("api-key", args, "ssh-key")

    assert [item.role for item in owned] == ["syncer", "learner-0", "learner-1"]
    assert [item.instance_id for item in owned] == ["id-0", "id-1", "id-2"]
    assert sleeps == [45.0, 45.0]


def test_l5_retry_operation_retries_transient_subprocess_failure(monkeypatch) -> None:
    import subprocess

    runner = _load_runner()
    attempts = {"count": 0}
    sleeps: list[float] = []

    def flaky_operation():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise subprocess.CalledProcessError(255, ["ssh"])
        return "ok"

    monkeypatch.setattr(runner.time, "sleep", sleeps.append)

    assert runner._retry_operation("flaky", flaky_operation, attempts=2, delay_seconds=7) == "ok"
    assert attempts["count"] == 2
    assert sleeps == [7]


def test_l5_runner_learner_command_includes_reconnect_timeout() -> None:
    runner = _load_runner()
    args = type(
        "Args",
        (),
        {
            "port": 28080,
            "run_id": "lambda-l5-reconnect",
            "trainer_type": "torch_causal_lm",
            "trainer_config_json": '{"device":"cuda","optimizer":"adamw"}',
            "steps": 8,
            "local_steps_per_sync": 1,
            "payload_storage_mode": "chunked",
            "checkpoint_storage_mode": "chunked",
            "merge_mode": "streaming_chunked",
            "global_update_storage_mode": "chunked",
            "chunk_size_mb": 1,
            "inline_payload_max_bytes": 1024,
            "artifact_transfer_mode": "object_store",
            "artifact_storage_backend": "auto",
            "learner_reconnect_timeout_seconds": 90.0,
        },
    )()

    command = runner._learner_command(args, "learner-0", "127.0.0.1")

    assert "--reconnect-timeout-seconds 90.0" in command


def test_l5_remote_committed_rounds_retries_transient_ssh(monkeypatch) -> None:
    import subprocess

    runner = _load_runner()
    syncer = runner.Instance("syncer", "id", "127.0.0.1", "us-east-1", "gpu_1x_a10")
    args = type("Args", (), {"ssh_private_key": "key"})()
    attempts = {"count": 0}
    sleeps: list[float] = []

    def fake_ssh(_ip, _key, _command, *, timeout):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise subprocess.CalledProcessError(255, ["ssh"])
        return type("Result", (), {"stdout": "3\n"})()

    monkeypatch.setattr(runner, "_ssh", fake_ssh)
    monkeypatch.setattr(runner.time, "sleep", sleeps.append)

    assert runner._remote_committed_rounds(syncer, args) == 3
    assert attempts["count"] == 2
    assert sleeps == [2.0]


def test_l5_runner_uses_configurable_learner_run_timeout(monkeypatch, tmp_path) -> None:
    runner = _load_runner()
    syncer = runner.Instance("syncer", "sid", "127.0.0.1", "us-east-1", "gpu_1x_a10")
    learner = runner.Instance("learner-0", "lid", "127.0.0.2", "us-east-1", "gpu_1x_a10")
    waits: list[int] = []

    class Proc:
        def poll(self):
            return 0

        def wait(self, timeout):
            waits.append(timeout)
            return 0

    args = type(
        "Args",
        (),
        {
            "ssh_private_key": tmp_path / "key",
            "learners": 1,
            "learner_run_timeout_seconds": 900.0,
            "restart_after_round": 1,
        },
    )()

    monkeypatch.setattr(runner, "_learner_command", lambda *_args: "true")
    monkeypatch.setattr(runner.subprocess, "Popen", lambda *_args, **_kwargs: Proc())
    monkeypatch.setattr(runner, "_remote_committed_rounds", lambda *_args: 2)
    monkeypatch.setattr(runner, "_shutdown_syncer", lambda *_args: None)
    monkeypatch.setattr(runner, "_start_syncer", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runner, "_wait_remote_file", lambda *_args: None)
    monkeypatch.setattr(runner, "_wait_direct_tcp", lambda *_args: None)

    runner._run_learners_with_restart([syncer, learner], syncer, args, tmp_path)

    assert waits == [900]


def test_l5_runner_commands_include_s3_runtime_args_when_enabled() -> None:
    runner = _load_runner()
    args = type(
        "Args",
        (),
        {
            "port": 28080,
            "run_id": "lambda-l5-s3",
            "trainer_type": "torch_causal_lm",
            "trainer_config_json": '{"device":"cuda","optimizer":"adamw"}',
            "vector_dim": 1234,
            "learners": 2,
            "steps": 8,
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
            "artifact_storage_backend": "s3_compatible",
            "s3_endpoint_url": "https://object.example.invalid",
            "s3_bucket": "bucket",
            "s3_prefix": "runs/test",
            "s3_region": "us-east-1",
            "s3_access_key_ref": "AWS_ACCESS_KEY_ID",
            "s3_secret_key_ref": "AWS_SECRET_ACCESS_KEY",
            "s3_session_token_ref": None,
            "learner_reconnect_timeout_seconds": 90.0,
        },
    )()

    commands = [
        runner._syncer_command(args),
        runner._learner_command(args, "learner-0", "127.0.0.1"),
    ]
    for command in commands:
        assert "--artifact-storage-backend s3_compatible" in command
        assert "--s3-endpoint-url https://object.example.invalid" in command
        assert "--s3-bucket bucket" in command
        assert "--s3-prefix runs/test" in command
        assert "--s3-access-key-ref AWS_ACCESS_KEY_ID" in command
        assert "--s3-secret-key-ref AWS_SECRET_ACCESS_KEY" in command


def test_l5_s3_runtime_env_prefix_is_used_without_secret_values() -> None:
    runner = _load_runner()
    args = type("Args", (), {"artifact_storage_backend": "s3_compatible"})()

    prefix = runner._remote_env_prefix(args)

    assert "s3_runtime_env.sh" in prefix
    assert "AWS_SECRET_ACCESS_KEY=" not in prefix


def test_l5_remote_dependency_install_includes_boto3_for_s3_backend() -> None:
    runner = _load_runner()
    args = type("Args", (), {"artifact_storage_backend": "s3_compatible"})()

    command = runner._remote_dependency_install_command(args)

    assert "pydantic" in command
    assert "boto3" in command


def test_l5_shutdown_syncer_retries_transient_shutdown_failure(monkeypatch) -> None:
    import subprocess

    runner = _load_runner()
    syncer = runner.Instance("syncer", "id", "127.0.0.1", "us-east-1", "gpu_1x_a10")
    args = type("Args", (), {"ssh_private_key": "key", "port": 28080, "run_id": "run"})()
    attempts = {"count": 0}
    sleeps: list[float] = []

    def fake_ssh(_ip, _key, remote, *, timeout):
        attempts["count"] += 1
        assert "timeout_seconds=30" in remote
        assert timeout == 120
        if attempts["count"] == 1:
            raise subprocess.CalledProcessError(1, ["ssh"])
        return type("Result", (), {"stdout": "{}"})()

    monkeypatch.setattr(runner, "_ssh", fake_ssh)
    monkeypatch.setattr(runner.time, "sleep", sleeps.append)
    monkeypatch.setattr(runner, "_wait_for_background_procs", lambda *, timeout: None)

    runner._shutdown_syncer(syncer, args)

    assert attempts["count"] == 2
    assert sleeps == [5.0]
