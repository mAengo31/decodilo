from __future__ import annotations

from decodilo.dev.parameter_fragment_smoke import (
    load_parameter_fragment_smoke_report,
    run_parameter_fragment_smoke,
)


def test_parameter_fragment_smoke_report_verifies_synthetic_fragments(tmp_path):
    report_path = tmp_path / "parameter-fragment-smoke.json"

    report = run_parameter_fragment_smoke(
        synthetic=True,
        fragments=2,
        max_steps=1,
        out=report_path,
    )
    loaded = load_parameter_fragment_smoke_report(report_path)

    assert report.parameter_fragment_smoke_status == "passed"
    assert loaded.parameter_fragment_smoke_status == "passed"
    assert loaded.parameter_fragment_semantics == "synthetic_vector_fragments"
    assert loaded.fragment_count == 2
    assert loaded.fragment_ids == ["fragment_0", "fragment_1"]
    assert loaded.fragment_ranges == [[0, 1], [2, 3]]
    assert loaded.fragment_shapes == [[2], [2]]
    assert loaded.fragment_versions_before == {"fragment_0": 0, "fragment_1": 0}
    assert loaded.fragment_versions_after == {"fragment_0": 0, "fragment_1": 1}
    assert loaded.fragment_state_roundtrip_check_passed is True
    assert loaded.fragment_update_check_passed is True
    assert loaded.fragment_merge_check_passed is True
    assert loaded.fragment_reconstruction_check_passed is True
    assert loaded.fragment_schedule_check_passed is True
    assert loaded.per_fragment_reference_check_passed is True
    assert loaded.global_reference_check_passed is True
    assert loaded.max_abs_error == 0.0
    assert loaded.overlap_semantics == "not_exercised"
    assert loaded.quantization_semantics == "not_exercised"
    assert loaded.network_used is False
    assert loaded.download_attempted is False
    assert loaded.training_attempted is False
    assert loaded.real_model_training_attempted is False
    assert loaded.torch_required is False
    assert loaded.gpu_required is False
    assert loaded.background_process_started is False
    assert loaded.launch_ready is False
    assert loaded.launch_allowed is False
    assert report_path.stat().st_size == loaded.artifact_bytes
    assert loaded.artifact_bytes < 32_768


def test_parameter_fragment_smoke_invalid_args_are_bounded_failure(tmp_path):
    report_path = tmp_path / "parameter-fragment-smoke-failed.json"

    report = run_parameter_fragment_smoke(
        synthetic=True,
        fragments=1,
        max_steps=1,
        out=report_path,
    )

    assert report.parameter_fragment_smoke_status == "failed"
    assert report.failed_check == "argument_validation"
    assert report.error_classification == "invalid_arguments"
    assert report.parameter_fragment_semantics == "not_exercised"
    assert report.network_used is False
    assert report.download_attempted is False
    assert report.real_model_training_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report_path.stat().st_size < 32_768
