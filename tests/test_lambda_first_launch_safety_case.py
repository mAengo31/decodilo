from lambda_m023_helpers import write_m023_core_artifacts

from decodilo.lambda_cloud.first_launch_safety_case import (
    build_lambda_first_launch_safety_case,
)


def test_safety_case_cannot_pass_without_fake_lifecycle_evidence(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)

    safety = build_lambda_first_launch_safety_case(
        proposal_ref=refs["proposal"],
        operation_spec=refs["operation"],
        fake_lifecycle_evidence_ref=tmp_path / "missing-readiness.json",
    )

    assert safety.safety_case_passed is False
    assert "missing fake lifecycle evidence" in safety.blockers
    assert safety.launch_allowed is False


def test_safety_case_passes_with_fake_evidence_and_policy(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)

    safety = build_lambda_first_launch_safety_case(
        proposal_ref=refs["proposal"],
        operation_spec=refs["operation"],
        fake_lifecycle_evidence_ref=refs["readiness"],
    )

    assert safety.safety_case_passed is True
    assert any(claim.claim_id == "idempotency_required" for claim in safety.claims)
    assert any(
        mode.mode_id == "duplicate_launch_request"
        for mode in safety.failure_mode_table.failure_modes
    )
    assert safety.real_mutation_enabled is False
