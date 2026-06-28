from __future__ import annotations

from lambda_m082_helpers import make_m081r2_workdir

from decodilo.lambda_cloud.diloco_synthetic_success_record import (
    build_lambda_diloco_synthetic_success_record_from_paths,
)


def test_diloco_synthetic_success_record_passes_for_m081r2(tmp_path):
    workdir = make_m081r2_workdir(tmp_path)

    record = build_lambda_diloco_synthetic_success_record_from_paths(workdir=workdir)

    assert record.success_status == "remote_diloco_shaped_synthetic_success"
    assert record.diloco_smoke_command_passed is True
    assert record.diloco_smoke_status == "passed"
    assert record.optimization_fidelity == "diloco_shaped_protocol_only"
    assert record.inner_optimizer_semantics == "synthetic_placeholder"
    assert record.outer_optimizer_semantics == "token_weighted_merge"
    assert record.parameter_fragment_semantics == "not_exercised"
    assert record.final_instance_count == 0
    assert record.final_unmanaged_count == 0
    assert record.launch_ready is False
    assert record.launch_allowed is False
