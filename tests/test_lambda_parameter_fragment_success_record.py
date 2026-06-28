from __future__ import annotations

from lambda_m088_helpers import make_m087r_workdir

from decodilo.lambda_cloud.parameter_fragment_success_record import (
    build_lambda_parameter_fragment_success_record_from_paths,
)


def test_parameter_fragment_success_record_captures_m087r_success(tmp_path):
    report = build_lambda_parameter_fragment_success_record_from_paths(
        workdir=make_m087r_workdir(tmp_path),
    )

    assert report.success_status == "remote_parameter_fragment_smoke_success"
    assert report.infrastructure_passed is True
    assert report.parameter_fragment_smoke_command_passed is True
    assert report.parameter_fragment_smoke_status == "passed"
    assert report.parameter_fragment_semantics == "synthetic_vector_fragments"
    assert report.fragment_count == 2
    assert report.fragment_update_check_passed is True
    assert report.fragment_merge_check_passed is True
    assert report.fragment_reconstruction_check_passed is True
    assert report.fragment_schedule_check_passed is True
    assert report.fragment_state_roundtrip_check_passed is True
    assert report.per_fragment_reference_check_passed is True
    assert report.global_reference_check_passed is True
    assert report.overlap_semantics == "not_exercised"
    assert report.quantization_semantics == "not_exercised"
    assert report.termination_verified is True
    assert report.final_instance_count == 0
    assert report.final_unmanaged_count == 0
    assert report.launch_ready is False
    assert report.launch_allowed is False
