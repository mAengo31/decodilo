from __future__ import annotations

from lambda_m084_helpers import make_m083r_workdir

from decodilo.lambda_cloud.diloco_optimizer_success_record import (
    build_lambda_diloco_optimizer_success_record_from_paths,
)


def test_diloco_optimizer_success_record_passes_for_m083r(tmp_path):
    workdir = make_m083r_workdir(tmp_path)

    record = build_lambda_diloco_optimizer_success_record_from_paths(workdir=workdir)

    assert record.success_status == "remote_diloco_optimizer_smoke_success"
    assert record.diloco_optimizer_smoke_command_passed is True
    assert record.diloco_optimizer_smoke_status == "passed"
    assert record.optimization_fidelity == "optimizer_semantics_smoke"
    assert record.inner_optimizer_semantics == "adamw"
    assert record.outer_optimizer_semantics == "nesterov"
    assert record.parameter_fragment_semantics == "not_exercised"
    assert record.pseudo_gradient_check_passed is True
    assert record.inner_adamw_check_passed is True
    assert record.outer_nesterov_check_passed is True
    assert record.optimizer_state_roundtrip_check_passed is True
    assert record.reference_value_check_passed is True
    assert record.max_abs_error == 0.0
    assert record.selected_region == "us-west-1"
    assert record.final_instance_count == 0
    assert record.final_unmanaged_count == 0
    assert record.launch_ready is False
    assert record.launch_allowed is False
