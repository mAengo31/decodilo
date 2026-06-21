from decodilo.lambda_cloud.no_training_policy import (
    build_lambda_no_training_policy,
    training_command_blocked,
)


def test_no_training_policy_blocks_training_and_benchmarks():
    report = build_lambda_no_training_policy()

    assert report.training_allowed is False
    assert training_command_blocked("torchrun train.py")
    assert training_command_blocked("python benchmark.py")
    assert report.launch_ready is False
    assert report.launch_allowed is False
