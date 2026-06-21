from decodilo.runtime.remote_backend_review_package import (
    build_remote_backend_review_package,
    write_remote_backend_review_package,
)


def test_review_package_builds_and_hashes_complete_artifacts(tmp_path) -> None:
    paths = {}
    for name in ["proposal", "decision", "risk", "rollout", "guard"]:
        path = tmp_path / f"{name}.json"
        path.write_text(f'{{"name":"{name}"}}\n', encoding="utf-8")
        paths[name] = path

    package = build_remote_backend_review_package(
        proposal_ref=paths["proposal"],
        decision_record_ref=paths["decision"],
        risk_register_ref=paths["risk"],
        rollout_plan_ref=paths["rollout"],
        sdk_guard_report_ref=paths["guard"],
    )

    assert package.blockers == []
    assert package.evidence_review.passed is True
    assert package.remote_backend_enabled is False
    out = tmp_path / "review-package.json"
    write_remote_backend_review_package(out, package)
    assert out.exists()


def test_review_package_missing_proposal_fails() -> None:
    package = build_remote_backend_review_package(
        proposal_ref="/tmp/does-not-exist-proposal.json",
        decision_record_ref="/tmp/does-not-exist-decision.json",
        risk_register_ref="/tmp/does-not-exist-risk.json",
        rollout_plan_ref="/tmp/does-not-exist-rollout.json",
        sdk_guard_report_ref="/tmp/does-not-exist-guard.json",
    )

    assert package.blockers
