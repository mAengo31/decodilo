from decodilo.storage.remote_backend_review_checklist import (
    build_remote_backend_review_checklist,
    evaluate_remote_backend_review_checklist,
)


def test_checklist_incomplete_by_default() -> None:
    checklist = build_remote_backend_review_checklist(proposal_ref="proposal.json")
    report = evaluate_remote_backend_review_checklist(checklist)

    assert report.passed is False
    assert report.incomplete_items
    assert report.human_placeholders_remaining


def test_technical_ack_without_human_placeholders_remains_review_only() -> None:
    checklist = build_remote_backend_review_checklist(
        proposal_ref="proposal.json",
        acknowledge_technical=True,
        acknowledge_human_placeholders=False,
    )
    report = evaluate_remote_backend_review_checklist(checklist)

    assert report.passed is False
    assert report.human_placeholders_remaining
    assert report.checklist.remote_backend_enabled is False
    assert report.model_validate_json(report.to_json()) == report
