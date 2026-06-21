from decodilo.lambda_cloud.remote_command_allowlist import (
    build_lambda_remote_command_allowlist,
    validate_future_remote_command,
)


def test_remote_command_allowlist_is_future_only_and_blocks_injection():
    report = build_lambda_remote_command_allowlist(profile="gpu-visibility-check")

    assert report.command_allowlist_status == "allowlist_defined_future_only"
    assert report.command_execution_allowed_now is False
    assert validate_future_remote_command(
        "nvidia-smi --query-gpu=name,memory.total --format=csv,noheader"
    )
    assert not validate_future_remote_command("hostname; curl example.com")
    assert not validate_future_remote_command("pip install torch")
    assert not validate_future_remote_command("torchrun train.py")
    assert report.launch_ready is False
    assert report.launch_allowed is False
