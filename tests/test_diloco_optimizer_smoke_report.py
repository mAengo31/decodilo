from __future__ import annotations

from decodilo.dev.diloco_optimizer_smoke import (
    EXPECTED_POST_OUTER_PARAMETERS,
    load_diloco_optimizer_smoke_report,
    run_diloco_optimizer_smoke,
)


def test_diloco_optimizer_smoke_report_verifies_optimizer_semantics(tmp_path):
    report_path = tmp_path / "diloco-optimizer-smoke.json"

    report = run_diloco_optimizer_smoke(
        synthetic=True,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
        out=report_path,
    )
    loaded = load_diloco_optimizer_smoke_report(report_path)

    assert report.diloco_optimizer_smoke_status == "passed"
    assert loaded.diloco_optimizer_smoke_status == "passed"
    assert loaded.optimization_fidelity == "optimizer_semantics_smoke"
    assert loaded.inner_optimizer_semantics == "adamw"
    assert loaded.outer_optimizer_semantics == "nesterov"
    assert loaded.parameter_fragment_semantics == "not_exercised"
    assert loaded.pseudo_gradient_check_passed is True
    assert loaded.inner_adamw_check_passed is True
    assert loaded.outer_nesterov_check_passed is True
    assert loaded.optimizer_state_roundtrip_check_passed is True
    assert loaded.reference_value_check_passed is True
    assert loaded.max_abs_error == 0.0
    assert loaded.expected_post_outer_parameters == EXPECTED_POST_OUTER_PARAMETERS
    assert loaded.post_outer_parameters == EXPECTED_POST_OUTER_PARAMETERS
    assert loaded.training_attempted is False
    assert loaded.real_model_training_attempted is False
    assert loaded.torch_required is False
    assert loaded.gpu_required is False
    assert loaded.background_process_started is False
    assert loaded.launch_ready is False
    assert loaded.launch_allowed is False
    assert report_path.stat().st_size == loaded.artifact_bytes
    assert loaded.artifact_bytes < 32_768


def test_diloco_optimizer_smoke_invalid_args_are_bounded_failure(tmp_path):
    report_path = tmp_path / "diloco-optimizer-smoke-failed.json"

    report = run_diloco_optimizer_smoke(
        synthetic=True,
        inner_optimizer="adamw",
        outer_optimizer="sgd",
        max_steps=1,
        out=report_path,
    )

    assert report.diloco_optimizer_smoke_status == "failed"
    assert report.failed_check == "argument_validation"
    assert report.error_classification == "invalid_arguments"
    assert report.optimization_fidelity == "not_verified"
    assert report.network_used is False
    assert report.download_attempted is False
    assert report.real_model_training_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report_path.stat().st_size < 32_768
