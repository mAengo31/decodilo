from __future__ import annotations

from lambda_m064_helpers import write_m064_chain

from decodilo.lambda_cloud.gpu_visibility_parsed_output_audit import (
    build_lambda_gpu_visibility_parsed_output_audit_from_paths,
)


def test_gpu_visibility_parsed_output_audit_detects_parsed_fields(tmp_path):
    paths = write_m064_chain(tmp_path, parsed_fields=True)

    audit = build_lambda_gpu_visibility_parsed_output_audit_from_paths(
        success_record=paths["success"],
        output_policy=paths["gpu_output_policy"],
    )

    assert audit.parsed_output_audit_status == "parsed_fields_present"
    assert audit.recommended_action == "accept_full_gpu_visibility_closeout"


def test_gpu_visibility_parsed_output_audit_detects_hash_only(tmp_path):
    paths = write_m064_chain(tmp_path)

    audit = build_lambda_gpu_visibility_parsed_output_audit_from_paths(
        success_record=paths["success"],
        output_policy=paths["gpu_output_policy"],
    )

    assert audit.parsed_output_audit_status == "output_hash_only"
    assert audit.recommended_action == "accept_hash_only_with_warning"
    assert audit.launch_ready is False
    assert audit.launch_allowed is False
