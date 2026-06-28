from __future__ import annotations

from decodilo.lambda_cloud.integrated_diloco_command_discovery import (
    LambdaIntegratedDilocoCommandDiscovery,
    write_lambda_integrated_diloco_command_discovery,
)
from decodilo.lambda_cloud.integrated_diloco_policy import (
    build_lambda_integrated_diloco_policy_from_path,
)


def test_integrated_diloco_policy_passes_for_safe_integrated_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_integrated_diloco_command_discovery(
        discovery_path,
        LambdaIntegratedDilocoCommandDiscovery(
            discovery_status="found_safe_integrated_diloco_command",
            argv_tokens=[
                "env",
                "PYTHONPATH=/tmp/decodilo-runtime:/tmp/decodilo-src/src",
                "python3",
                "-m",
                "decodilo.cli",
                "dev",
                "integrated-diloco-smoke",
                "--synthetic",
                "--learners",
                "1",
                "--sync-rounds",
                "1",
                "--inner-optimizer",
                "adamw",
                "--outer-optimizer",
                "nesterov",
                "--max-steps",
                "1",
                "--out",
                "/tmp/decodilo-integrated-diloco-smoke.json",
            ],
            timeout_seconds=120,
            inner_optimizer="adamw",
            outer_optimizer="nesterov",
            expected_integrated_fidelity="integrated_optimizer_protocol_smoke",
        ),
    )

    report = build_lambda_integrated_diloco_policy_from_path(
        command_discovery=discovery_path,
    )

    assert report.policy_status == "policy_passed"
    assert report.one_bounded_integrated_diloco_command is True
    assert report.expected_integrated_fidelity == "integrated_optimizer_protocol_smoke"
    assert report.learners == 1
    assert report.sync_rounds == 1
    assert report.inner_optimizer == "adamw"
    assert report.outer_optimizer == "nesterov"
    assert report.no_real_training is True
    assert report.no_internet is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_integrated_diloco_policy_blocks_without_safe_command(tmp_path):
    discovery_path = tmp_path / "discovery.json"
    write_lambda_integrated_diloco_command_discovery(
        discovery_path,
        LambdaIntegratedDilocoCommandDiscovery(
            discovery_status="no_safe_integrated_diloco_command_found",
            blockers=["no_safe_integrated_diloco_command_found"],
        ),
    )

    report = build_lambda_integrated_diloco_policy_from_path(
        command_discovery=discovery_path,
    )

    assert report.policy_status == "blocked_no_safe_command"
    assert "no_safe_integrated_diloco_command_found" in report.blockers
    assert report.no_real_training is True
    assert report.no_internet is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
