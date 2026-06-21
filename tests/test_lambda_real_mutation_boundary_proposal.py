from lambda_m023_helpers import write_m023_core_artifacts, write_text_evidence
from pydantic import ValidationError

from decodilo.lambda_cloud.real_mutation_boundary_proposal import (
    LambdaRealMutationBoundaryProposal,
    build_lambda_real_mutation_boundary_proposal,
)


def test_proposal_builds_from_fake_evidence(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)

    proposal = build_lambda_real_mutation_boundary_proposal(
        m019c_discovery=refs["discovery"],
        m020_report=refs["m020"],
        m022_readiness_package=refs["readiness"],
        real_mutation_absence_audit=refs["absence"],
    )

    assert proposal.boundary_status == "review_ready"
    assert "no training" in proposal.non_goals.items
    assert proposal.real_mutation_transport_implemented is False
    assert proposal.launch_allowed is False


def test_proposal_missing_fake_readiness_blocks(tmp_path) -> None:
    discovery = write_text_evidence(tmp_path, "discovery.json")
    m020 = write_text_evidence(tmp_path, "m020.json")
    absence = write_text_evidence(tmp_path, "absence.json")

    proposal = build_lambda_real_mutation_boundary_proposal(
        m019c_discovery=discovery,
        m020_report=m020,
        m022_readiness_package=tmp_path / "missing-readiness.json",
        real_mutation_absence_audit=absence,
    )

    assert proposal.boundary_status == "evidence_incomplete"
    assert any("fake launch readiness" in blocker for blocker in proposal.blockers)


def test_proposal_rejects_enabled_flags(tmp_path) -> None:
    refs = write_m023_core_artifacts(tmp_path)
    proposal = build_lambda_real_mutation_boundary_proposal(
        m019c_discovery=refs["discovery"],
        m020_report=refs["m020"],
        m022_readiness_package=refs["readiness"],
        real_mutation_absence_audit=refs["absence"],
    )

    try:
        LambdaRealMutationBoundaryProposal(
            **proposal.model_copy(update={"launch_allowed": True}).model_dump()
        )
    except ValidationError as exc:
        assert "cannot enable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("enabled proposal accepted")
