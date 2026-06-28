from __future__ import annotations

from lambda_m086_helpers import make_m085r_workdir

from decodilo.lambda_cloud.integrated_diloco_success_record import (
    build_lambda_integrated_diloco_success_record_from_paths,
)


def test_integrated_diloco_success_record_passes_for_m085r(tmp_path):
    workdir = make_m085r_workdir(tmp_path)

    record = build_lambda_integrated_diloco_success_record_from_paths(workdir=workdir)

    assert record.success_status == "remote_integrated_diloco_synthetic_success"
    assert record.integrated_diloco_smoke_command_passed is True
    assert record.integrated_diloco_smoke_status == "passed"
    assert record.optimization_fidelity == "integrated_optimizer_protocol_smoke"
    assert record.parameter_fragment_semantics == "not_exercised"
    assert record.protocol_optimizer_link_check_passed is True
    assert record.max_abs_error == 0.0
    assert record.launch_ready is False
    assert record.launch_allowed is False
