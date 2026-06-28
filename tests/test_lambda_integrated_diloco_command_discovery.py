from __future__ import annotations

from decodilo.lambda_cloud.integrated_diloco_command_discovery import (
    LambdaIntegratedDilocoCommandDiscovery,
    discover_lambda_integrated_diloco_command,
)


def test_integrated_diloco_discovery_finds_local_command():
    report = discover_lambda_integrated_diloco_command(source_root=".")

    assert report.discovery_status == "found_safe_integrated_diloco_command"
    assert report.argv_tokens == [
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
    ]
    assert report.expected_integrated_fidelity == "integrated_optimizer_protocol_smoke"
    assert report.no_real_training is True
    assert report.no_external_network is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_integrated_diloco_discovery_no_command_artifact_is_fail_closed():
    report = LambdaIntegratedDilocoCommandDiscovery(
        discovery_status="no_safe_integrated_diloco_command_found",
        blockers=["no_safe_integrated_diloco_command_found"],
        recommendation=(
            "python -m decodilo.cli dev integrated-diloco-smoke --synthetic "
            "--learners 1 --sync-rounds 1 --inner-optimizer adamw "
            "--outer-optimizer nesterov --max-steps 1 "
            "--out /tmp/decodilo-integrated-diloco-smoke.json"
        ),
    )

    assert report.discovery_status == "no_safe_integrated_diloco_command_found"
    assert report.argv_tokens == []
    assert "integrated-diloco-smoke" in (report.recommendation or "")
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_integrated_diloco_discovery_rejects_unsafe_flags():
    try:
        LambdaIntegratedDilocoCommandDiscovery(
            discovery_status="found_safe_integrated_diloco_command",
            argv_tokens=["env", "python3", "-m", "decodilo.cli"],
            timeout_seconds=120,
            inner_optimizer="adamw",
            outer_optimizer="nesterov",
            expected_integrated_fidelity="integrated_optimizer_protocol_smoke",
            no_external_network=False,
        )
    except ValueError as exc:
        assert "unsafe flags" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("unsafe integrated command was accepted")
