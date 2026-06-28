from __future__ import annotations

from decodilo.lambda_cloud.bounded_diloco_experiment_discovery import (
    LambdaBoundedDilocoExperimentCommandDiscovery,
    discover_lambda_bounded_diloco_experiment_command,
)


def test_bounded_diloco_discovery_fails_closed_when_command_missing():
    report = discover_lambda_bounded_diloco_experiment_command(source_root=".")

    assert (
        report.discovery_status
        == "found_safe_bounded_diloco_experiment_command"
    )
    assert report.command_category == "dev_bounded_diloco_experiment_one_step"
    assert report.argv_tokens == [
        "env",
        "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
        "python3",
        "-m",
        "decodilo.cli",
        "dev",
        "bounded-diloco-experiment",
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--fragments",
        "2",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
        "--out",
        "/tmp/decodilo-bounded-diloco-experiment.json",
    ]
    assert report.timeout_seconds == 180
    assert report.learners == 1
    assert report.sync_rounds == 1
    assert report.fragments == 2
    assert report.inner_optimizer == "adamw"
    assert report.outer_optimizer == "nesterov"
    assert report.max_steps == 1
    assert report.no_external_network is True
    assert report.no_package_install is True
    assert report.no_downloads is True
    assert report.no_real_training is True
    assert report.no_new_independent_smoke_category is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_bounded_diloco_discovery_rejects_unsafe_found_command_flags():
    try:
        LambdaBoundedDilocoExperimentCommandDiscovery(
            discovery_status="found_safe_bounded_diloco_experiment_command",
            argv_tokens=["python3"],
            timeout_seconds=30,
            no_real_training=False,
        )
    except ValueError as exc:
        assert "unsafe flags" in str(exc)
    else:
        raise AssertionError("unsafe bounded experiment discovery was accepted")
