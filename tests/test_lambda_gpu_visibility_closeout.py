from __future__ import annotations

from lambda_m064_helpers import write_m064_chain

from decodilo.lambda_cloud.gpu_visibility_closeout import (
    build_lambda_gpu_visibility_closeout_from_paths,
)


def test_gpu_visibility_closeout_success_with_parsed_fields(tmp_path):
    paths = write_m064_chain(tmp_path, parsed_fields=True)

    closeout = build_lambda_gpu_visibility_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
        parsed_output_audit=paths["parsed_audit"],
    )

    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.closeout_succeeded is True
    assert closeout.parsed_fields_present is True


def test_gpu_visibility_closeout_hash_only_is_warning_not_failure(tmp_path):
    paths = write_m064_chain(tmp_path)

    closeout = build_lambda_gpu_visibility_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
        parsed_output_audit=paths["parsed_audit"],
    )

    assert closeout.closeout_status == "closed_with_warnings"
    assert closeout.closeout_succeeded is True
    assert closeout.parsed_output_status == "output_hash_only"
