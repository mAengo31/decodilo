from __future__ import annotations

from lambda_m064_helpers import write_m064_chain

from decodilo.lambda_cloud.gpu_visibility_evidence_package import (
    build_lambda_gpu_visibility_evidence_package_from_paths,
)


def test_gpu_visibility_evidence_package_passes_hash_only_chain(tmp_path):
    paths = write_m064_chain(tmp_path)

    package = build_lambda_gpu_visibility_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        parsed_output_audit=paths["parsed_audit"],
    )

    assert package.evidence_complete is True
    assert package.parsed_output_status == "output_hash_only"
    assert package.gpu_visibility_command_success is True
    assert package.launch_ready is False
    assert package.launch_allowed is False


def test_gpu_visibility_evidence_package_blocks_missing_journal(tmp_path):
    paths = write_m064_chain(tmp_path)
    (paths["workdir"] / "journal.jsonl").unlink()

    package = build_lambda_gpu_visibility_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        parsed_output_audit=paths["parsed_audit"],
    )

    assert package.evidence_complete is False
    assert "missing_evidence:journal" in package.blockers
